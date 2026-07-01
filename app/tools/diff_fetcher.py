"""Fetch PR diffs from GitHub / Gitea."""
from __future__ import annotations
import httpx
from app.core.config import settings


def _parse_repo(repo_url: str) -> tuple[str, str]:
    parts = repo_url.rstrip("/").removesuffix(".git").split("/")
    return parts[-2], parts[-1]


async def list_open_prs(repo_url: str, limit: int = 5) -> list[dict]:
    """Return open PRs for a repo (up to `limit`)."""
    org, repo = _parse_repo(repo_url)
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {settings.git_token}",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"https://api.github.com/repos/{org}/{repo}/pulls",
            headers=headers,
            params={"state": "open", "per_page": limit},
        )
        resp.raise_for_status()
        return [
            {
                "number":     pr["number"],
                "title":      pr["title"],
                "author":     pr["user"]["login"],
                "created_at": pr["created_at"],
                "url":        pr["html_url"],
            }
            for pr in resp.json()
        ]


async def fetch_pr_diff(repo_url: str, pr_number: int) -> str:
    """Fetch the unified diff for a pull request."""
    org, repo = _parse_repo(repo_url)

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
    org, repo = _parse_repo(repo_url)

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
