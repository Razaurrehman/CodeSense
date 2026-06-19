"""Fetch changelogs for npm / pip package version bumps."""
from __future__ import annotations
from dataclasses import dataclass
import httpx


@dataclass
class Changelog:
    package:         str
    from_version:    str
    to_version:      str
    ecosystem:       str
    breaking_changes:bool
    summary:         str
    url:             str


async def fetch(
    package: str,
    from_version: str,
    to_version: str,
    ecosystem: str = "npm",
) -> Changelog:
    """
    Fetch changelog / release notes for a version bump.

    Args:
        package:      Package name.
        from_version: Current version.
        to_version:   Target version.
        ecosystem:    npm | pip | nuget

    Returns:
        Changelog dataclass.
    """
    if ecosystem == "npm":
        return await _npm_changelog(package, from_version, to_version)
    elif ecosystem == "pip":
        return await _pypi_changelog(package, from_version, to_version)
    else:
        return Changelog(
            package=package, from_version=from_version,
            to_version=to_version, ecosystem=ecosystem,
            breaking_changes=False, summary="Changelog not available for this ecosystem.",
            url="",
        )


async def _npm_changelog(package: str, from_v: str, to_v: str) -> Changelog:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"https://registry.npmjs.org/{package}/{to_v}")
            resp.raise_for_status()
            data = resp.json()
            description = data.get("description", "")
            repo_url    = data.get("repository", {}).get("url", "").replace("git+", "").replace(".git", "")
            summary     = description[:500] if description else "No description available."
        except httpx.HTTPError:
            summary  = "Could not fetch changelog."
            repo_url = ""

    breaking = _detect_breaking(summary, from_v, to_v)
    return Changelog(
        package=package, from_version=from_v, to_version=to_v,
        ecosystem="npm", breaking_changes=breaking,
        summary=summary, url=repo_url,
    )


async def _pypi_changelog(package: str, from_v: str, to_v: str) -> Changelog:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(f"https://pypi.org/pypi/{package}/{to_v}/json")
            resp.raise_for_status()
            data    = resp.json()
            info    = data.get("info", {})
            summary = info.get("summary", "")[:500] or "No summary available."
            url     = info.get("project_url", f"https://pypi.org/project/{package}")
        except httpx.HTTPError:
            summary = "Could not fetch changelog."
            url     = ""

    breaking = _detect_breaking(summary, from_v, to_v)
    return Changelog(
        package=package, from_version=from_v, to_version=to_v,
        ecosystem="pip", breaking_changes=breaking,
        summary=summary, url=url,
    )


def _detect_breaking(summary: str, from_v: str, to_v: str) -> bool:
    """Heuristic: major version bump or keywords in summary."""
    text    = summary.lower()
    has_kw  = any(k in text for k in ("breaking", "removed", "deprecated", "incompatible"))
    # Major version bump (e.g. 1.x.x → 2.x.x)
    try:
        from_major = int(from_v.split(".")[0])
        to_major   = int(to_v.split(".")[0])
        major_bump = to_major > from_major
    except (ValueError, IndexError):
        major_bump = False
    return has_kw or major_bump
