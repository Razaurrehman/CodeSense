"""Fetch PR diffs from GitHub / Gitea."""
from __future__ import annotations
import httpx
from app.core.config import settings


async def fetch_pr_diff(repo_url: str, pr_number: int) -> str:
    """
    Fetch the unified diff for a pull request.

    Args:
        repo_url:   Full GitHub repo URL (https://github.com/org/repo).
        pr_number:  Pull request number.

    Returns:
        Unified diff string.
    """
    # Parse org/repo from URL
    parts = repo_url.rstrip("/").split("/")
    org, repo = parts[-2], parts[-1]

    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "Authorization": f"Bearer {settings.git_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.text


async def fetch_pr_metadata(repo_url: str, pr_number: int) -> dict:
    """Fetch PR title, description, and changed files."""
    parts = repo_url.rstrip("/").split("/")
    org, repo = parts[-2], parts[-1]

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {settings.git_token}",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        pr_resp = await client.get(
            f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}",
            headers=headers,
        )
        files_resp = await client.get(
            f"https://api.github.com/repos/{org}/{repo}/pulls/{pr_number}/files",
            headers=headers,
        )
        pr_resp.raise_for_status()
        files_resp.raise_for_status()

        pr   = pr_resp.json()
        files = files_resp.json()

        return {
            "title":        pr.get("title", ""),
            "description":  pr.get("body", ""),
            "author":       pr.get("user", {}).get("login", ""),
            "changed_files": [f["filename"] for f in files],
            "additions":    sum(f.get("additions", 0) for f in files),
            "deletions":    sum(f.get("deletions", 0) for f in files),
        }
