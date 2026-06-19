"""Read raw file content from indexed repositories."""
from __future__ import annotations
from pathlib import Path
import httpx
from app.core.config import settings


async def read_file(
    repo_name: str,
    file_path: str,
    line_range: tuple[int, int] | None = None,
) -> str:
    """
    Read file content from a local clone or GitHub API.

    Args:
        repo_name:   Name of the repository (from repos.yaml).
        file_path:   Relative file path within the repo.
        line_range:  Optional (start_line, end_line) tuple (1-indexed).

    Returns:
        Raw file content string.
    """
    # Try local clone first
    local_path = Path("/repos") / repo_name / file_path
    if local_path.exists():
        content = local_path.read_text(encoding="utf-8", errors="replace")
        if line_range:
            lines = content.splitlines()
            start, end = line_range
            content = "\n".join(lines[start - 1:end])
        return content

    # Fall back to GitHub API
    return await _read_from_github(repo_name, file_path, line_range)


async def _read_from_github(
    repo_name: str,
    file_path: str,
    line_range: tuple[int, int] | None,
) -> str:
    import yaml
    config_path = Path(settings.repos_config_path)
    if not config_path.exists():
        return ""

    repos = yaml.safe_load(config_path.read_text()).get("repos", [])
    repo_cfg = next((r for r in repos if r["name"] == repo_name), None)
    if not repo_cfg:
        return ""

    parts = repo_cfg["url"].rstrip("/").split("/")
    org, repo = parts[-2], parts[-1]
    branch   = repo_cfg.get("branch", "main")

    headers = {
        "Accept": "application/vnd.github.v3.raw",
        "Authorization": f"Bearer {settings.git_token}",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{org}/{repo}/contents/{file_path}",
            headers=headers,
            params={"ref": branch},
        )
        resp.raise_for_status()
        content = resp.text

    if line_range:
        lines   = content.splitlines()
        start, end = line_range
        content = "\n".join(lines[start - 1:end])

    return content
