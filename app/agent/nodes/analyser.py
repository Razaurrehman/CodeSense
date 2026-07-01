"""Analyser node — runs static analysis, vulnerability, and license tools."""
import asyncio
from app.agent.state import AgentState
from app.tools import static_analyzer, vuln_scanner, license_checker, changelog_fetcher
from app.core.config import settings
from pathlib import Path

SOURCE_EXTENSIONS = {".js", ".ts", ".tsx", ".jsx", ".py", ".go", ".java", ".cs"}
CHUNK_LINES = 80
MAX_CHUNKS  = 25

LICENSE_FILE_NAMES = {
    "LICENSE", "LICENSE.md", "LICENSE.txt", "LICENSE.rst",
    "COPYING", "COPYING.md", "COPYING.txt", "NOTICE",
}


def collect_license_files(repo_root: Path) -> list[dict]:
    """Collect LICENSE files + package manifests (which carry license fields)."""
    skip_dirs = {"node_modules", ".git", "__pycache__", ".next", "dist", "build", ".venv", "venv"}
    files = []
    for f in sorted(repo_root.rglob("*")):
        if any(part in skip_dirs for part in f.parts):
            continue
        if f.is_file() and (f.name in LICENSE_FILE_NAMES or f.name in MANIFEST_NAMES):
            try:
                content = f.read_text(errors="ignore")
                rel = str(f.relative_to(repo_root))
                files.append({
                    "file": rel,
                    "content": content[:3000],
                    "start_line": 1,
                    "end_line": len(content.splitlines()),
                    "chunk_index": len(files) + 1,
                    "total_chunks": 0,
                })
            except Exception:
                pass
    for i, m in enumerate(files):
        m["total_chunks"] = len(files)
        m["chunk_index"] = i + 1
    return files


MANIFEST_NAMES = {
    "package.json", "requirements.txt", "pyproject.toml", "setup.py",
    "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "packages.config",
    "composer.json", "Gemfile", "Pipfile", "yarn.lock",
}


def collect_manifests(repo_root: Path) -> list[dict]:
    """Collect all dependency manifest files from the repo."""
    skip_dirs = {"node_modules", ".git", "__pycache__", ".next", "dist", "build", ".venv", "venv"}
    manifests = []
    for f in sorted(repo_root.rglob("*")):
        if any(part in skip_dirs for part in f.parts):
            continue
        if f.is_file() and f.name in MANIFEST_NAMES:
            try:
                content = f.read_text(errors="ignore")
                rel = str(f.relative_to(repo_root))
                manifests.append({
                    "file": rel,
                    "content": content[:3000],
                    "start_line": 1,
                    "end_line": len(content.splitlines()),
                    "chunk_index": len(manifests) + 1,
                    "total_chunks": 0,
                })
            except Exception:
                pass
    for i, m in enumerate(manifests):
        m["total_chunks"] = len(manifests)
        m["chunk_index"] = i + 1
    return manifests


def _chunk_file(file_path: Path, repo_root: Path, chunk_lines: int = CHUNK_LINES) -> list[dict]:
    """Split a source file into line-based chunks."""
    try:
        lines = file_path.read_text(errors="ignore").splitlines()
    except Exception:
        return []
    rel = str(file_path.relative_to(repo_root))
    chunks = []
    for i in range(0, len(lines), chunk_lines):
        chunk_lines_slice = lines[i:i + chunk_lines]
        chunks.append({
            "file":    rel,
            "content": "\n".join(chunk_lines_slice),
            "start_line": i + 1,
            "end_line":   i + len(chunk_lines_slice),
        })
    return chunks


def collect_chunks(repo_root: Path, max_chunks: int = MAX_CHUNKS) -> list[dict]:
    """Walk repo and collect chunks from source files."""
    all_chunks: list[dict] = []
    skip_dirs = {"node_modules", ".git", "__pycache__", ".next", "dist", "build", ".venv", "venv"}
    for f in sorted(repo_root.rglob("*")):
        if any(part in skip_dirs for part in f.parts):
            continue
        if f.suffix in SOURCE_EXTENSIONS and f.is_file():
            all_chunks.extend(_chunk_file(f, repo_root))
            if len(all_chunks) >= max_chunks:
                break
    total = len(all_chunks)
    for idx, chunk in enumerate(all_chunks[:max_chunks]):
        chunk["chunk_index"] = idx + 1
        chunk["total_chunks"] = min(total, max_chunks)
    return all_chunks[:max_chunks]


async def _ensure_cloned(repo_url: str) -> Path:
    """Clone repo if not already present in /repos. Returns local path."""
    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    local = Path("/repos") / repo_name
    if local.exists():
        return local

    local.mkdir(parents=True, exist_ok=True)
    token = settings.git_token
    if token and repo_url.startswith("https://github.com"):
        auth_url = repo_url.replace("https://", f"https://{token}@")
    else:
        auth_url = repo_url

    proc = await asyncio.create_subprocess_exec(
        "git", "clone", "--depth=1", auth_url, str(local),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.communicate()
    return local


async def analyser_node(state: AgentState) -> AgentState:
    """Run appropriate analysis tools based on user story."""
    req     = state.raw_request
    us      = state.user_story
    outputs = state.tool_outputs.copy()

    # ── Bug scan ───────────────────────────────────────────────────
    if us in ("bug_scan", "similar_bugs", "pr_review", "explain_code", "refactor", "generate_tests", "migration_plan", "impact_analysis", "version_bump", "license_check", "vuln_scan"):
        repo_url = req.get("repo", "") or (req.get("repos") or [""])[0]
        scope    = req.get("scope", ".")
        if repo_url:
            local = await _ensure_cloned(repo_url)
            scan_path = str(local / scope.lstrip("/")) if scope and scope != "." else str(local)
            if not Path(scan_path).exists():
                scan_path = str(local)

            # Static analysis (semgrep + grep) — skip for explain_code, refactor, generate_tests
            if us not in ("explain_code", "refactor", "generate_tests", "migration_plan", "impact_analysis", "version_bump", "license_check", "vuln_scan"):
                findings = await static_analyzer.analyze(scan_path)
                outputs["static_findings"] = [
                    {
                        "rule_id":   f.rule_id,
                        "severity":  f.severity,
                        "file_path": f.file_path,
                        "line":      f.line,
                        "message":   f.message,
                        "fix":       f.fix,
                    }
                    for f in findings[:15]
                ]

            # Code chunks for per-chunk LLM analysis
            if us in ("bug_scan", "explain_code", "refactor", "similar_bugs", "generate_tests", "migration_plan", "impact_analysis"):
                outputs["code_chunks"] = collect_chunks(local)
            elif us == "version_bump":
                outputs["code_chunks"] = collect_manifests(local)
            elif us == "license_check":
                outputs["code_chunks"] = collect_license_files(local)
            elif us == "vuln_scan":
                outputs["code_chunks"] = collect_manifests(local)

    # ── Vulnerability scan ─────────────────────────────────────────
    if us == "vuln_scan":
        all_cves = []
        threshold = req.get("alert_threshold", "HIGH")

        for repo in req.get("repos", []):
            local = Path("/repos") / repo.split("/")[-1]
            path  = str(local) if local.exists() else repo
            cves  = await vuln_scanner.scan(path, threshold)
            for cve in cves:
                all_cves.append({
                    "cve_id":            cve.cve_id,
                    "severity":          cve.severity,
                    "cvss_score":        cve.cvss_score,
                    "package":           cve.package,
                    "affected_version":  cve.affected_version,
                    "fixed_version":     cve.fixed_version,
                    "exploit_available": cve.exploit_available,
                    "description":       cve.description,
                    "repo":              repo,
                })

        for image in req.get("images", []):
            cves = await vuln_scanner.scan(image, threshold)
            for cve in cves:
                all_cves.append({
                    **cve.__dict__,
                    "repo": image,
                })

        outputs["cve_findings"] = sorted(all_cves, key=lambda x: x["cvss_score"], reverse=True)

    # ── License check ──────────────────────────────────────────────
    if us == "license_check":
        all_licenses = []
        for repo in req.get("repos", []):
            local     = Path("/repos") / repo.split("/")[-1]
            repo_path = str(local) if local.exists() else "."
            repo_name = repo.split("/")[-1]
            lics      = await license_checker.check(repo_path, repo_name)
            all_licenses.extend([l.__dict__ for l in lics])
        outputs["license_findings"] = all_licenses

    # ── Version bump ───────────────────────────────────────────────
    if us == "version_bump":
        # In production: parse manifests and compare to latest registry versions.
        # Here we prepare the structure; actual diff is done in llm_reasoner.
        outputs["version_bump_repos"] = req.get("repos", [])
        outputs["ecosystem"]          = req.get("ecosystem", "all")

    state.tool_outputs = outputs
    return state
