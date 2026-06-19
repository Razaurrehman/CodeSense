"""Semgrep static analysis wrapper."""
from __future__ import annotations
import asyncio
import json
from dataclasses import dataclass


@dataclass
class StaticFinding:
    rule_id:   str
    severity:  str
    file_path: str
    line:      int
    message:   str
    fix:       str = ""


async def analyze(
    path: str,
    rules: list[str] | None = None,
    extra_config: str | None = None,
) -> list[StaticFinding]:
    """
    Run Semgrep on a file or directory.

    Args:
        path:         File or directory path.
        rules:        Semgrep rule packs (default: p/ci p/security p/owasp).
        extra_config: Path to custom Semgrep YAML rule file.

    Returns:
        List of StaticFinding objects.
    """
    if rules is None:
        rules = ["p/ci", "p/security", "p/owasp"]

    cmd = ["semgrep", "--json", "--quiet"]
    for rule in rules:
        cmd += ["--config", rule]
    if extra_config:
        cmd += ["--config", extra_config]
    cmd.append(path)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    findings: list[StaticFinding] = []
    try:
        data = json.loads(stdout.decode())
        for result in data.get("results", []):
            findings.append(StaticFinding(
                rule_id=result.get("check_id", ""),
                severity=result.get("extra", {}).get("severity", "WARNING"),
                file_path=result.get("path", ""),
                line=result.get("start", {}).get("line", 0),
                message=result.get("extra", {}).get("message", ""),
                fix=result.get("extra", {}).get("fix", ""),
            ))
    except (json.JSONDecodeError, KeyError):
        pass

    return findings
