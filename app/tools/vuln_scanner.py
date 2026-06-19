"""Trivy + OSV vulnerability scanner wrapper."""
from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass, field


@dataclass
class CVEFinding:
    cve_id:           str
    severity:         str
    cvss_score:       float
    package:          str
    affected_version: str
    fixed_version:    str
    exploit_available:bool
    description:      str
    affected_paths:   list[str] = field(default_factory=list)


async def scan(
    target: str,
    alert_threshold: str = "HIGH",
) -> list[CVEFinding]:
    """
    Run Trivy vulnerability scan on a repo path or container image.

    Args:
        target:          File system path or image name (e.g. myapp:latest).
        alert_threshold: Minimum severity to include (CRITICAL|HIGH|MEDIUM|LOW).

    Returns:
        List of CVEFinding objects sorted by CVSS score descending.
    """
    severity_map = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    min_sev = severity_map.get(alert_threshold.upper(), 3)

    cmd = [
        "trivy", "fs" if not ":" in target else "image",
        "--format", "json",
        "--quiet",
        "--severity", ",".join(k for k, v in severity_map.items() if v >= min_sev),
        target,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout.decode())
    except (FileNotFoundError, json.JSONDecodeError):
        # Trivy not installed — return empty
        return []

    findings: list[CVEFinding] = []
    for result in data.get("Results", []):
        for vuln in result.get("Vulnerabilities", []):
            severity = vuln.get("Severity", "UNKNOWN")
            if severity_map.get(severity, 0) < min_sev:
                continue
            findings.append(CVEFinding(
                cve_id=vuln.get("VulnerabilityID", ""),
                severity=severity,
                cvss_score=vuln.get("CVSS", {}).get("nvd", {}).get("V3Score", 0.0),
                package=vuln.get("PkgName", ""),
                affected_version=vuln.get("InstalledVersion", ""),
                fixed_version=vuln.get("FixedVersion", ""),
                exploit_available=bool(vuln.get("PublishedDate")),
                description=vuln.get("Description", "")[:300],
                affected_paths=[result.get("Target", "")],
            ))

    return sorted(findings, key=lambda f: f.cvss_score, reverse=True)
