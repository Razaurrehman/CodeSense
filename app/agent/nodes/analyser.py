"""Analyser node — runs static analysis, vulnerability, and license tools."""
from app.agent.state import AgentState
from app.tools import static_analyzer, vuln_scanner, license_checker, changelog_fetcher
from pathlib import Path


async def analyser_node(state: AgentState) -> AgentState:
    """Run appropriate analysis tools based on user story."""
    req     = state.raw_request
    us      = state.user_story
    outputs = state.tool_outputs.copy()

    # ── Bug scan ───────────────────────────────────────────────────
    if us in ("bug_scan", "similar_bugs", "pr_review"):
        scope = req.get("scope") or req.get("repo", "")
        if scope:
            # Map repo name → local path
            local = Path("/repos") / scope.rstrip("/").split("/")[-1]
            scan_path = str(local) if local.exists() else scope
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
                for f in findings
            ]

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
