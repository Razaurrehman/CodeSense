"""License compliance checker (licensee + manual manifest parsing)."""
from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path


RISK_TIERS = {
    "MIT": "Permissive", "Apache-2.0": "Permissive", "BSD-2-Clause": "Permissive",
    "BSD-3-Clause": "Permissive", "ISC": "Permissive", "0BSD": "Permissive",
    "LGPL-2.1": "Weak-Copyleft", "LGPL-3.0": "Weak-Copyleft", "MPL-2.0": "Weak-Copyleft",
    "GPL-2.0": "Strong-Copyleft", "GPL-3.0": "Strong-Copyleft",
    "AGPL-3.0": "Network-Copyleft",
    "UNKNOWN": "Unknown", "UNLICENSED": "Proprietary",
}


@dataclass
class LicenseFinding:
    name:         str
    version:      str
    license_id:   str
    risk_tier:    str
    repo:         str
    manifest:     str


async def check(repo_path: str, repo_name: str = "") -> list[LicenseFinding]:
    """
    Scan a repo path for dependency licenses.

    Args:
        repo_path:  Local path to the repository root.
        repo_name:  Name of the repository (for output).

    Returns:
        List of LicenseFinding objects.
    """
    findings: list[LicenseFinding] = []
    root = Path(repo_path)

    # npm — package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        findings.extend(await _scan_npm(pkg_json, repo_name))

    # pip — requirements.txt
    req_txt = root / "requirements.txt"
    if req_txt.exists():
        findings.extend(await _scan_pip(req_txt, repo_name))

    return findings


async def _scan_npm(manifest: Path, repo_name: str) -> list[LicenseFinding]:
    """Use npm list --json to get license info."""
    findings: list[LicenseFinding] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "npm", "list", "--json", "--all",
            cwd=str(manifest.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode())
        _flatten_npm(data.get("dependencies", {}), findings, str(manifest), repo_name)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return findings


def _flatten_npm(deps: dict, results: list, manifest: str, repo: str):
    for name, info in deps.items():
        lic       = info.get("license", "UNKNOWN")
        version   = info.get("version", "")
        risk      = RISK_TIERS.get(lic, "Unknown")
        results.append(LicenseFinding(
            name=name, version=version, license_id=lic,
            risk_tier=risk, repo=repo, manifest=manifest,
        ))
        _flatten_npm(info.get("dependencies", {}), results, manifest, repo)


async def _scan_pip(manifest: Path, repo_name: str) -> list[LicenseFinding]:
    """Use pip-licenses to get license info."""
    findings: list[LicenseFinding] = []
    try:
        proc = await asyncio.create_subprocess_exec(
            "pip-licenses", "--format=json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode())
        for pkg in data:
            lic  = pkg.get("License", "UNKNOWN")
            risk = RISK_TIERS.get(lic, "Unknown")
            findings.append(LicenseFinding(
                name=pkg.get("Name", ""),
                version=pkg.get("Version", ""),
                license_id=lic,
                risk_tier=risk,
                repo=repo_name,
                manifest=str(manifest),
            ))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return findings
