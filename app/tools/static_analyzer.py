"""Static analysis — semgrep with grep-pattern fallback."""
from __future__ import annotations
import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StaticFinding:
    rule_id:   str
    severity:  str
    file_path: str
    line:      int
    message:   str
    fix:       str = ""


# Grep-based patterns for common security issues (JS/TS/Python)
GREP_PATTERNS = [
    ("hardcoded-secret",      "HIGH",   r'(password|secret|api_key|apikey|token)\s*=\s*["\'][^"\']{6,}["\']', "Possible hardcoded secret"),
    ("eval-usage",            "HIGH",   r'\beval\s*\(',                                                         "Use of eval() is dangerous"),
    ("dangerouslySetInnerHTML","HIGH",  r'dangerouslySetInnerHTML',                                             "XSS risk via dangerouslySetInnerHTML"),
    ("sql-concat",            "HIGH",   r'(query|sql)\s*[+]=?\s*["\'].*\+',                                    "Possible SQL injection via string concat"),
    ("innerHTML",             "MEDIUM", r'\.innerHTML\s*=',                                                     "XSS risk via innerHTML assignment"),
    ("console-log",           "LOW",    r'\bconsole\.(log|error|warn)\(',                                       "Debug console statement left in code"),
    ("todo-fixme",            "LOW",    r'(TODO|FIXME|HACK|XXX):',                                             "Unresolved TODO/FIXME comment"),
    ("http-url",              "MEDIUM", r'http://(?!localhost|127\.0\.0\.1)',                                   "Insecure HTTP URL (use HTTPS)"),
    ("process-env-exposed",   "MEDIUM", r'res\.(json|send)\(.*process\.env',                                   "Possible env variable exposure in response"),
    ("no-input-validation",   "MEDIUM", r'req\.(body|query|params)\.\w+\s*[^=!<>]',                           "Request input used without validation"),
]


async def _semgrep_scan(path: str, rules: list[str]) -> list[StaticFinding] | None:
    """Try semgrep. Returns None if semgrep is broken/unavailable."""
    cmd = [
        "semgrep", "--json", "--quiet",
        "--timeout", "30",
        "--max-target-bytes", "500000",
        "--jobs", "2",
    ]
    for rule in rules:
        cmd += ["--config", rule]
    cmd.append(path)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        if proc.returncode not in (0, 1):
            return None

        data = json.loads(stdout.decode())
        return [
            StaticFinding(
                rule_id=r.get("check_id", ""),
                severity=r.get("extra", {}).get("severity", "WARNING"),
                file_path=r.get("path", ""),
                line=r.get("start", {}).get("line", 0),
                message=r.get("extra", {}).get("message", ""),
                fix=r.get("extra", {}).get("fix", ""),
            )
            for r in data.get("results", [])
        ]
    except Exception:
        return None


async def _grep_scan(path: str) -> list[StaticFinding]:
    """Grep-based pattern scanner — works on any codebase."""
    findings: list[StaticFinding] = []
    extensions = {".js", ".ts", ".tsx", ".jsx", ".py", ".env", ".json"}

    for pattern_id, severity, pattern, message in GREP_PATTERNS:
        cmd = [
            "grep", "-rn", "--include=*.js", "--include=*.ts",
            "--include=*.tsx", "--include=*.jsx", "--include=*.py",
            "-E", pattern, path
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            for line in stdout.decode().splitlines()[:5]:
                parts = line.split(":", 2)
                if len(parts) >= 2:
                    findings.append(StaticFinding(
                        rule_id=f"grep/{pattern_id}",
                        severity=severity,
                        file_path=parts[0].replace(path, "").lstrip("/"),
                        line=int(parts[1]) if parts[1].isdigit() else 0,
                        message=message,
                        fix="",
                    ))
        except Exception:
            continue

    return findings


async def analyze(
    path: str,
    rules: list[str] | None = None,
    extra_config: str | None = None,
) -> list[StaticFinding]:
    if rules is None:
        rules = ["p/ci"]

    semgrep_results, grep_results = await asyncio.gather(
        _semgrep_scan(path, rules),
        _grep_scan(path),
    )
    combined = (semgrep_results or []) + grep_results
    return combined[:15]
