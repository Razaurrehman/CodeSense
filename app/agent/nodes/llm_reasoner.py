"""LLM reasoner node — synthesises all context into findings."""
from __future__ import annotations
import json
import asyncio
from app.agent.state import AgentState
from app.core.llm import get_llm

SYSTEM_PROMPT = """\
You are CodeSense, an AI-powered Code Intelligence Agent for professional engineering teams.

OUTPUT RULES — STRICTLY ENFORCED:
- Output ONLY structured markdown. No letters, no greetings, no sign-offs.
- Never write "Dear [Recipient]", "Best regards", or any prose introduction.
- Every finding must use the exact template blocks shown in each task prompt.
- Cite real file paths and line numbers only. If unknown, write "line: unknown".
- Label confidence: [CRITICAL] [HIGH] [MEDIUM] [LOW] and [VERIFIED] [INFERRED] [POSSIBLE].
- You are a PROPOSAL ENGINE — never apply changes, only propose them.
- No padding, no filler sentences. If you have nothing to report, write "No findings."
"""

TASK_PROMPTS: dict[str, str] = {

"pr_review": """\
Review ALL open pull requests listed below. For each PR produce a separate review block.

Output EXACTLY in this format:

## Open PRs Summary
- Total open PRs reviewed: <N>

---

## PR #<number> — <title> by @<author>
**URL**: <url>
**Verdict**: APPROVE / REQUEST CHANGES / COMMENT
**Issues**: Critical: <N> | High: <N> | Medium: <N> | Low: <N>

### Issues

#### [PR<number>-001] <short title>
| Field | Value |
|---|---|
| Severity | CRITICAL / HIGH / MEDIUM / LOW |
| File | path/to/file:line |
| Category | Security / Logic / Style / Tests / Performance |

**Issue**: One sentence.
**Fix**: Concrete suggestion.

---

(Repeat the ## PR #<number> block for each PR. If a PR has no issues write "No issues found — APPROVE".)

All PRs data (diffs + metadata): {diff}
Parsed file symbols: {parsed_files}
RAG similar patterns: {rag_context}
Static analysis findings: {static_findings}
""",

"bug_scan": """\
Analyse the static analysis findings and RAG context to identify real bugs.
Filter false positives. Add semantic bugs the static analyser missed.

Output EXACTLY in this format — no deviations:

## Summary
- Total findings: <N>
- Critical: <N> | High: <N> | Medium: <N> | Low: <N>

---

## Findings

### [BUG-001] <short title>
| Field | Value |
|---|---|
| Severity | CRITICAL / HIGH / MEDIUM / LOW |
| File | path/to/file.py |
| Line | <number or unknown> |
| Confidence | VERIFIED / INFERRED / POSSIBLE |

**What**: One sentence describing the bug.
**Why it matters**: One sentence on the impact.
**Fix**: Concrete fix recommendation in one or two sentences.

---

(Repeat ### [BUG-002] block for each finding. If no bugs found, write "## No findings detected.")

Static findings: {static_findings}
RAG context: {rag_context}
Scope: {scope}
""",

"explain_code": """\
Explain the provided code in plain language for a senior engineer.
Output per the Code Explanation format (Section D US-3).

File content: {file_content}
AST structure: {ast}
Call graph (callers / implementors): {call_graph}
RAG similar patterns: {rag_context}
""",

"refactor": """\
Propose a refactoring of the target code toward the stated goal.
Output as a unified diff patch per the Refactoring Proposal format (Section D US-4).

Goal: {goal}
File content: {file_content}
Cross-repo callers: {call_graph}
RAG similar patterns: {rag_context}
""",

"similar_bugs": """\
Given the known bug, identify semantically similar bugs in the RAG results.
Auto-generate a Semgrep rule to detect this pattern.
Output per the Similar Bug Detection Report format (Section D US-5).

Known bug: {known_bug}
RAG candidates (re-rank these): {rag_context}
""",

"generate_tests": """\
Generate a complete test file for the target function/class.
Cover: happy path, edge cases, null/empty, boundaries, exceptions, async paths.
Output per the Test Generation Report format (Section D US-6).

Target: {target}
Framework: {framework}
File content: {file_content}
AST structure: {ast}
Existing test style (from RAG): {rag_context}
""",

"migration_plan": """\
Produce a phased strangler-fig migration plan for the target component.
Output per the Migration Plan format (Section D US-7).

Component: {component}
Target stack: {target_stack}
File content: {file_content}
AST (public interface): {ast}
Dependents (from call graph): {call_graph}
""",

"impact_analysis": """\
Analyse all call sites for the proposed symbol change.
Classify each site and estimate effort.
Output per the Impact Analysis format (Section D US-8).

Symbol: {symbol}
Proposed change: {proposed_change}
Call graph: {call_graph}
RAG callers context: {rag_context}
""",

"version_bump": """\
Review the provided dependency manifests and propose safe version bumps.
Highlight breaking changes, CVEs fixed, and license changes.
Output per the Dependency Update Report format (Section D US-9).

Repos: {repos}
Ecosystem: {ecosystem}
RAG context: {rag_context}
""",

"license_check": """\
Analyse the license findings and flag compliance risks for the project type.
Output per the License Compliance Report format (Section D US-10).

Project type: {project_type}
License findings: {license_findings}
""",

"vuln_scan": """\
Analyse the CVE findings and produce a prioritised vulnerability report.

Output EXACTLY in this format:

## Summary
- Total CVEs: <N>
- Critical: <N> | High: <N> | Medium: <N> | Low: <N>
- Alert threshold: {alert_threshold}

---

## Vulnerabilities

### [CVE-001] <CVE-ID or title>
| Field | Value |
|---|---|
| Severity | CRITICAL / HIGH / MEDIUM / LOW |
| Package | package@version |
| Fixed in | version or "no fix available" |
| CVSS | score |

**Impact**: One sentence.
**Action**: Upgrade to X or apply workaround Y.

---

CVE findings: {cve_findings}
Alert threshold: {alert_threshold}
""",
}


def _build_prompt(state: AgentState) -> str:
    us      = state.user_story
    req     = state.raw_request
    outputs = state.tool_outputs
    rag_ctx = "\n\n".join(
        f"[{c.repo_name}/{c.file_path}:{c.start_line}] (score={c.score})\n{c.content[:300]}"
        for c in state.rag_results[:8]
    )

    template = TASK_PROMPTS.get(us, "Analyse the following request:\n{raw_request}")

    variables = {
        "rag_context":       rag_ctx,
        "raw_request":       json.dumps(req, indent=2),
        # PR review
        "pr_meta":           json.dumps(outputs.get("pr_meta", {})),
        "parsed_files":      json.dumps(outputs.get("parsed_files", [])),
        "diff":              (outputs.get("diff", ""))[:4000],
        "static_findings":   json.dumps(outputs.get("static_findings", [])),
        # Code
        "file_content":      (outputs.get("file_content", ""))[:4000],
        "ast":               json.dumps(outputs.get("ast", {})),
        "call_graph":        json.dumps(outputs.get("call_graph", {})),
        # Per story
        "scope":             req.get("scope", ""),
        "target":            req.get("target", ""),
        "framework":         req.get("framework", "auto-detect"),
        "goal":              req.get("goal", ""),
        "component":         req.get("component", ""),
        "target_stack":      req.get("target_stack", ""),
        "symbol":            req.get("symbol", ""),
        "proposed_change":   req.get("proposed_change", ""),
        "known_bug":         req.get("known_bug", ""),
        "repos":             json.dumps(req.get("repos", [])),
        "ecosystem":         req.get("ecosystem", "all"),
        "project_type":      req.get("project_type", "commercial"),
        "license_findings":  json.dumps(outputs.get("license_findings", [])),
        "cve_findings":      json.dumps(outputs.get("cve_findings", []))[:4000],
        "alert_threshold":   req.get("alert_threshold", "HIGH"),
    }

    try:
        return template.format(**variables)
    except KeyError:
        return template + "\n\nRequest: " + json.dumps(req)


CHUNK_SYSTEM_PROMPT = """\
You are an expert code bug detection AI operating inside a RAG (Retrieval-Augmented Generation) pipeline.

You will receive one CODE CHUNK at a time along with its METADATA (file path, language, chunk index, total chunks, and optionally relevant context retrieved from a vector store).

## YOUR ROLE PER CHUNK
Analyze only the provided chunk. Do not assume code outside the chunk is correct or incorrect unless it appears in the RETRIEVED CONTEXT section.

## BUG CATEGORIES — scan every chunk for all of these:
1. Logic & semantic errors (off-by-one, wrong branching, dead code)
2. Null / undefined / type safety violations
3. Resource & memory leaks (handles, connections, allocations)
4. Concurrency & async bugs (race conditions, missing await, deadlocks)
5. Security vulnerabilities (injection, hardcoded secrets, XSS, path traversal)
6. Error handling gaps (swallowed exceptions, missing propagation)

## OUTPUT FORMAT — respond ONLY in this JSON structure:
{
  "chunk_id": "<chunk_index>/<total_chunks>",
  "file": "<file_path>",
  "language": "<detected_language>",
  "issues": [
    {
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "category": "<bug category>",
      "title": "<short title>",
      "line_hint": "<line number or range if identifiable>",
      "description": "<what the bug is and why it matters>",
      "snippet": "<1-5 line relevant code excerpt>",
      "fix": "<concrete corrected code or instruction>",
      "cwe": "<CWE-ID if applicable, else null>"
    }
  ],
  "chunk_summary": "<1-2 sentence summary of this chunk purpose>",
  "cross_chunk_flags": ["<suspicious pattern that may connect to other chunks>"]
}

## STRICT RULES
- Return ONLY valid JSON — no markdown, no preamble, no explanation outside the JSON.
- If no bugs are found, return "issues": [] — never omit the field.
- Always populate cross_chunk_flags — use [] if nothing flagged.
- Auto-detect language from the chunk — never ask.
- Do not hallucinate line numbers — use "unknown" if not determinable.
"""


def _chunk_prompt(chunk: dict, rag_ctx: str) -> str:
    return f"""\
METADATA:
- File: {chunk['file']}
- Chunk: {chunk['chunk_index']}/{chunk['total_chunks']}
- Lines: {chunk['start_line']}–{chunk['end_line']}

RETRIEVED CONTEXT (from vector store — related code patterns):
{rag_ctx or 'None'}

CODE CHUNK:
```
{chunk['content']}
```
"""


def _aggregate_to_markdown(results: list[dict]) -> str:
    all_issues = []
    cross_flags = []
    for r in results:
        for issue in r.get("issues", []):
            issue["_file"] = r.get("file", "unknown")
            all_issues.append(issue)
        cross_flags.extend(r.get("cross_chunk_flags", []))

    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_issues.sort(key=lambda x: sev_order.get(x.get("severity", "LOW"), 3))

    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for issue in all_issues:
        sev = issue.get("severity", "LOW")
        counts[sev] = counts.get(sev, 0) + 1

    lines = [
        "## Summary",
        f"- Total findings: {len(all_issues)}",
        f"- Critical: {counts['CRITICAL']} | High: {counts['HIGH']} | Medium: {counts['MEDIUM']} | Low: {counts['LOW']}",
        "",
        "---",
        "",
        "## Findings",
        "",
    ]

    if not all_issues:
        lines.append("## No findings detected.")
    else:
        for idx, issue in enumerate(all_issues, 1):
            lines += [
                f"### [BUG-{idx:03d}] {issue.get('title', 'Issue')}",
                "| Field | Value |",
                "|---|---|",
                f"| Severity | {issue.get('severity', 'UNKNOWN')} |",
                f"| File | {issue.get('_file', 'unknown')} |",
                f"| Line | {issue.get('line_hint', 'unknown')} |",
                f"| Category | {issue.get('category', '')} |",
                f"| CWE | {issue.get('cwe') or 'N/A'} |",
                "",
                f"**What**: {issue.get('description', '')}",
                f"**Fix**: {issue.get('fix', '')}",
            ]
            if issue.get("snippet"):
                lines += ["", f"```\n{issue['snippet']}\n```"]
            lines.append("")
            lines.append("---")
            lines.append("")

    if cross_flags:
        lines += ["## Cross-Chunk Flags", ""]
        for flag in cross_flags:
            lines.append(f"- {flag}")

    return "\n".join(lines)


async def _run_chunk_scan(chunks: list[dict], rag_ctx: str) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.0)
    except RuntimeError:
        llm = get_llm(temperature=0.0)

    async def _scan_one(chunk: dict) -> dict:
        prompt = _chunk_prompt(chunk, rag_ctx)
        try:
            resp = await llm.ainvoke([
                SystemMessage(content=CHUNK_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ])
            text = resp.content.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:])
                text = text.rsplit("```", 1)[0].strip()
            return json.loads(text)
        except Exception:
            return {"file": chunk["file"], "issues": [], "cross_chunk_flags": []}

    # Run up to 5 chunks concurrently
    results = []
    for i in range(0, len(chunks), 5):
        batch = chunks[i:i+5]
        batch_results = await asyncio.gather(*[_scan_one(c) for c in batch])
        results.extend(batch_results)

    return _aggregate_to_markdown(results)


EXPLAIN_SYSTEM_PROMPT = """\
You are CodeSense, an expert code intelligence agent. You will receive a set of source code chunks sampled from a repository.

Produce a comprehensive codebase explanation for a senior engineer joining the project.

Output EXACTLY in this format:

## Repository Overview
One paragraph describing the project's purpose and architecture style.

---

## Architecture
| Layer | Component | Role |
|---|---|---|
(Fill in the key architectural layers and their components)

---

## Key Modules
For each significant file or module found in the chunks:

### `<file_path>`
- **Purpose**: one sentence
- **Key exports / symbols**: list the main functions, classes, or constants
- **Dependencies**: notable imports or connections to other modules

---

## Data Flow
Describe the primary data flow through the system (e.g. request → handler → service → DB → response). Use bullet points.

---

## Entry Points
List the main entry points (API routes, CLI commands, event listeners, etc.).

---

## Notable Patterns & Conventions
List 3–6 patterns you observe (e.g. error handling style, async usage, naming conventions, framework choices).

---

STRICT RULES:
- Output ONLY the markdown above. No greetings, no sign-offs.
- Base all observations on the actual code chunks provided.
- If a section has no data, write "Not determinable from sampled chunks."
"""


async def _run_explain_scan(chunks: list[dict], repo_url: str) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.1)
    except RuntimeError:
        llm = get_llm(temperature=0.1)

    repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1] if repo_url else "repo"

    # Build a single combined prompt with all chunks
    chunk_text_parts = []
    for c in chunks:
        chunk_text_parts.append(
            f"### {c['file']} (lines {c['start_line']}–{c['end_line']})\n```\n{c['content'][:600]}\n```"
        )
    chunk_text = "\n\n".join(chunk_text_parts)

    human_msg = f"Repository: {repo_name}\nSampled chunks ({len(chunks)} total):\n\n{chunk_text}"

    resp = await llm.ainvoke([
        SystemMessage(content=EXPLAIN_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    return resp.content.strip()


REFACTOR_SYSTEM_PROMPT = """\
You are CodeSense, an expert refactoring analysis AI. You will receive source code chunks sampled from a repository.

Identify concrete refactoring opportunities across the codebase.

Output EXACTLY in this format:

## Summary
- Files analysed: <N>
- Refactoring opportunities: <N>
- High: <N> | Medium: <N> | Low: <N>

---

## Opportunities

### [REF-001] <short title>
| Field | Value |
|---|---|
| Priority | HIGH / MEDIUM / LOW |
| File | path/to/file |
| Lines | <range or unknown> |
| Category | Duplication / Complexity / Naming / Structure / Performance / Error Handling |

**Problem**: One sentence describing the issue.
**Refactor**: Concrete actionable suggestion.

```
<relevant code snippet>
```

---

(Repeat ### [REF-002] block for each opportunity. If no issues found, write "## No refactoring opportunities identified.")

STRICT RULES:
- Output ONLY the markdown above. No greetings, no sign-offs.
- Base observations solely on the provided chunks.
- Do not suggest style-only nits unless they impact readability significantly.
- Prioritise HIGH for: duplicated logic, missing error handling, deeply nested code, security-adjacent patterns.
"""


async def _run_refactor_scan(chunks: list[dict], repo_url: str) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.1)
    except RuntimeError:
        llm = get_llm(temperature=0.1)

    repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1] if repo_url else "repo"

    chunk_text_parts = []
    for c in chunks:
        chunk_text_parts.append(
            f"### {c['file']} (lines {c['start_line']}–{c['end_line']})\n```\n{c['content'][:600]}\n```"
        )
    chunk_text = "\n\n".join(chunk_text_parts)

    human_msg = f"Repository: {repo_name}\nSampled chunks ({len(chunks)} total):\n\n{chunk_text}"

    resp = await llm.ainvoke([
        SystemMessage(content=REFACTOR_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    return resp.content.strip()


SIMILAR_BUGS_SYSTEM_PROMPT = """\
You are CodeSense, an expert bug-pattern analysis AI. You will receive source code chunks sampled from a repository.

Identify recurring bug patterns — groups of similar issues that appear in multiple places across the codebase.

Output EXACTLY in this format:

## Summary
- Files analysed: <N>
- Bug patterns found: <N>

---

## Patterns

### [PAT-001] <pattern name>
| Field | Value |
|---|---|
| Severity | CRITICAL / HIGH / MEDIUM / LOW |
| Occurrences | <N> locations |
| Category | Security / Error Handling / Logic / Null Safety / Async / Resource Leak |

**Pattern**: One sentence describing the recurring bug pattern.
**Why it matters**: One sentence on the combined impact.
**Occurrences**:
- `<file>:<line_hint>` — <brief note>
- `<file>:<line_hint>` — <brief note>

**Fix**: Concrete fix that addresses all occurrences of this pattern.

---

(Repeat ### [PAT-002] block for each pattern. If no patterns found, write "## No recurring patterns detected.")

STRICT RULES:
- Output ONLY the markdown above. No greetings, no sign-offs.
- Only report patterns that appear in 2+ locations — single occurrences belong in Bug Scan, not here.
- Base all observations on the actual code chunks provided.
"""


async def _run_similar_bugs_scan(chunks: list[dict], repo_url: str) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.1)
    except RuntimeError:
        llm = get_llm(temperature=0.1)

    repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1] if repo_url else "repo"

    chunk_text_parts = []
    for c in chunks:
        chunk_text_parts.append(
            f"### {c['file']} (lines {c['start_line']}–{c['end_line']})\n```\n{c['content'][:600]}\n```"
        )
    chunk_text = "\n\n".join(chunk_text_parts)

    human_msg = f"Repository: {repo_name}\nSampled chunks ({len(chunks)} total):\n\n{chunk_text}"

    resp = await llm.ainvoke([
        SystemMessage(content=SIMILAR_BUGS_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    return resp.content.strip()


GENERATE_TESTS_SYSTEM_PROMPT = """\
You are CodeSense, an expert test-generation AI. You will receive source code chunks sampled from a repository.

Auto-detect the test framework from the codebase (look for vitest/jest/pytest/xUnit imports or config files).
Identify functions and classes that lack test coverage, then generate concrete test cases for them.

Output EXACTLY in this format:

## Summary
- Framework detected: <framework>
- Untested functions/classes found: <N>
- Test cases generated: <N>

---

## Generated Tests

### `<file_path>`

```<language>
<complete test file or test block ready to paste>
```

**Coverage**:
- [x] <what is tested>
- [x] <what is tested>
- [ ] <what is NOT covered and why>

---

(Repeat the ### `<file>` block for each file that needs tests. Prioritise files with the most logic and least coverage.)

STRICT RULES:
- Output ONLY the markdown above. No greetings, no sign-offs.
- Generate real, runnable test code — not pseudocode or placeholders.
- Cover: happy path, edge cases, null/empty inputs, error paths.
- If framework cannot be detected, default to the most common for the detected language (pytest for Python, vitest for JS/TS).
- Base all observations on the actual code chunks provided.
"""


async def _run_generate_tests_scan(chunks: list[dict], repo_url: str) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.1)
    except RuntimeError:
        llm = get_llm(temperature=0.1)

    repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1] if repo_url else "repo"

    chunk_text_parts = []
    for c in chunks:
        chunk_text_parts.append(
            f"### {c['file']} (lines {c['start_line']}–{c['end_line']})\n```\n{c['content'][:600]}\n```"
        )
    chunk_text = "\n\n".join(chunk_text_parts)

    human_msg = f"Repository: {repo_name}\nSampled chunks ({len(chunks)} total):\n\n{chunk_text}"

    resp = await llm.ainvoke([
        SystemMessage(content=GENERATE_TESTS_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    return resp.content.strip()


MIGRATION_PLAN_SYSTEM_PROMPT = """\
You are CodeSense, an expert migration planning AI. You will receive source code chunks sampled from a repository.

Analyse the codebase, identify legacy or high-risk components, and produce a phased strangler-fig migration plan.

Output EXACTLY in this format:

## Summary
- Tech stack detected: <detected stack>
- Legacy components identified: <N>
- Estimated migration phases: <N>
- Overall risk: LOW / MEDIUM / HIGH

---

## Legacy Components Identified

| Component | File | Risk | Reason |
|---|---|---|---|
| <name> | <file> | HIGH/MEDIUM/LOW | <one sentence> |

---

## Migration Plan

### Phase 1 — <phase title>
**Goal**: One sentence.
**Components**: List files/modules involved.
**Steps**:
1. <concrete step>
2. <concrete step>
**Risk**: LOW / MEDIUM / HIGH
**Effort**: <days estimate>

---

### Phase 2 — <phase title>
(repeat structure)

---

## Recommended Target Stack
Based on the detected language and patterns, recommend a modern equivalent stack with rationale.

---

STRICT RULES:
- Output ONLY the markdown above. No greetings, no sign-offs.
- Base all observations on the actual code chunks provided.
- Phases must be ordered from lowest risk to highest risk (strangler-fig pattern).
- If the codebase is already modern, write "## No migration needed — stack is current."
"""


async def _run_migration_plan_scan(chunks: list[dict], repo_url: str) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.1)
    except RuntimeError:
        llm = get_llm(temperature=0.1)

    repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1] if repo_url else "repo"

    chunk_text_parts = []
    for c in chunks:
        chunk_text_parts.append(
            f"### {c['file']} (lines {c['start_line']}–{c['end_line']})\n```\n{c['content'][:600]}\n```"
        )
    chunk_text = "\n\n".join(chunk_text_parts)

    human_msg = f"Repository: {repo_name}\nSampled chunks ({len(chunks)} total):\n\n{chunk_text}"

    resp = await llm.ainvoke([
        SystemMessage(content=MIGRATION_PLAN_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    return resp.content.strip()


IMPACT_ANALYSIS_SYSTEM_PROMPT = """\
You are CodeSense, an expert impact analysis AI. You will receive source code chunks sampled from a repository.

Identify the highest-impact symbols (functions, classes, modules) — those that are widely used, deeply depended upon, or whose change would cause the largest blast radius.

Output EXACTLY in this format:

## Summary
- Files analysed: <N>
- High-impact symbols identified: <N>
- Overall change risk: LOW / MEDIUM / HIGH

---

## Impact Map

### [IMP-001] `<symbol_name>`
| Field | Value |
|---|---|
| File | path/to/file |
| Type | Function / Class / Module / Constant |
| Blast Radius | HIGH / MEDIUM / LOW |
| Dependents | <estimated count or "multiple files"> |

**Why high-impact**: One sentence on why this symbol is critical.
**Change risk**: What breaks if this symbol is modified or removed.
**Recommendation**: One sentence — safe to change / refactor with caution / freeze until decoupled.

---

(Repeat ### [IMP-002] block for each symbol, ordered by blast radius descending.)

## Hotspot Files
List files that appear as dependency hubs — imported or referenced from many other files.

| File | Risk | Reason |
|---|---|---|
| <file> | HIGH/MEDIUM/LOW | <one sentence> |

---

STRICT RULES:
- Output ONLY the markdown above. No greetings, no sign-offs.
- Base all observations on the actual code chunks provided.
- Focus on real structural dependencies visible in the code, not speculative ones.
"""


async def _run_impact_analysis_scan(chunks: list[dict], repo_url: str) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.1)
    except RuntimeError:
        llm = get_llm(temperature=0.1)

    repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1] if repo_url else "repo"

    chunk_text_parts = []
    for c in chunks:
        chunk_text_parts.append(
            f"### {c['file']} (lines {c['start_line']}–{c['end_line']})\n```\n{c['content'][:600]}\n```"
        )
    chunk_text = "\n\n".join(chunk_text_parts)

    human_msg = f"Repository: {repo_name}\nSampled chunks ({len(chunks)} total):\n\n{chunk_text}"

    resp = await llm.ainvoke([
        SystemMessage(content=IMPACT_ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    return resp.content.strip()


VERSION_BUMP_SYSTEM_PROMPT = """\
You are CodeSense, an expert dependency analysis AI with up-to-date knowledge of package ecosystems.

You will receive dependency manifest files (package.json, requirements.txt, etc.) with their current pinned versions.

Use your training knowledge of package release histories to identify version bumps. You MUST recommend bumps for:
- Any package with a newer major version available (e.g. Express 4 → 5, React 18 → 19, Vite 5 → 6)
- Any package with known security advisories in the current version range
- Any package that is end-of-life or deprecated
- Any package significantly behind the latest stable minor/patch release

Output EXACTLY in this format:

## Summary
- Ecosystems detected: <list>
- Dependencies reviewed: <N>
- Bumps recommended: <N> (Critical: <N> | High: <N> | Medium: <N> | Low: <N>)

---

## Recommended Bumps

### `<manifest_file>` — <ecosystem>

| Package | Current | Recommended | Priority | Reason |
|---|---|---|---|---|
| <package> | <current version> | <specific version number> | CRITICAL/HIGH/MEDIUM/LOW | <specific reason> |

**Breaking changes**: List any breaking changes or migration steps for HIGH/CRITICAL bumps.

---

(Repeat the ### block for each manifest. If a manifest has no bumps needed, write "All packages current.")

STRICT RULES:
- Output ONLY the markdown above. No greetings, no sign-offs.
- Use SPECIFIC version numbers you know — never write "latest stable" when you know the version.
- Priority: CRITICAL = active CVE, HIGH = major version with breaking changes, MEDIUM = minor/patch with fixes, LOW = optional update.
- Do NOT say "all up to date" unless you have verified knowledge that the current version IS the latest release.
- Packages like express, react, vite, fastapi, django almost always have newer versions — check them carefully.
"""


async def _run_version_bump_scan(chunks: list[dict], repos: list) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.1)
    except RuntimeError:
        llm = get_llm(temperature=0.1)

    chunk_text_parts = []
    for c in chunks:
        chunk_text_parts.append(
            f"### {c['file']} (lines {c['start_line']}–{c['end_line']})\n```\n{c['content'][:800]}\n```"
        )
    chunk_text = "\n\n".join(chunk_text_parts)

    repo_names = ", ".join(repos) if repos else "repo"
    human_msg = f"Repositories: {repo_names}\nSampled chunks ({len(chunks)} total):\n\n{chunk_text}"

    resp = await llm.ainvoke([
        SystemMessage(content=VERSION_BUMP_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    return resp.content.strip()


LICENSE_CHECK_SYSTEM_PROMPT = """\
You are CodeSense, an expert open-source license compliance AI with knowledge of all major software licenses.

You will receive LICENSE files and package manifests from a repository. Analyse the project's own license and each dependency's license for compliance risks.

Output EXACTLY in this format:

## Summary
- Project license: <detected or "Not found">
- Dependencies reviewed: <N>
- Compliance risks: <N> (Critical: <N> | High: <N> | Medium: <N> | Low: <N>)

---

## Project License
**License**: <name>
**Type**: Permissive / Copyleft / Weak Copyleft / Proprietary / Unknown
**Summary**: One sentence on what this license allows and requires.

---

## Dependency Compliance

| Package | License | Risk | Reason |
|---|---|---|---|
| <package> | <license> | CRITICAL/HIGH/MEDIUM/LOW/OK | <one sentence> |

---

## Risk Details

### [LIC-001] <package> — <license>
**Risk**: CRITICAL / HIGH / MEDIUM / LOW
**Issue**: One sentence on the specific compliance problem.
**Action**: Concrete recommendation (replace with X / add attribution / obtain commercial license / safe to use).

---

(Repeat ### [LIC-002] for each risky dependency. If no risks, write "## No compliance risks detected.")

STRICT RULES:
- Output ONLY the markdown above. No greetings, no sign-offs.
- Use your training knowledge of license compatibility rules (GPL contamination, AGPL network use, LGPL linking, MIT/Apache permissiveness, etc.).
- CRITICAL: GPL/AGPL dependencies in a proprietary project.
- HIGH: LGPL without dynamic linking, CC-BY-SA in code.
- MEDIUM: Attribution required (MIT, Apache 2.0) but no NOTICE file detected.
- LOW: Unlicensed packages or unclear license declarations.
- OK: Fully compatible permissive licenses (MIT, Apache 2.0, BSD, ISC).
"""


async def _run_license_check_scan(chunks: list[dict], repos: list) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.1)
    except RuntimeError:
        llm = get_llm(temperature=0.1)

    chunk_text_parts = []
    for c in chunks:
        chunk_text_parts.append(
            f"### {c['file']}\n```\n{c['content'][:2000]}\n```"
        )
    chunk_text = "\n\n".join(chunk_text_parts)

    repo_names = ", ".join(repos) if repos else "repo"
    human_msg = f"Repositories: {repo_names}\nFiles found ({len(chunks)} total):\n\n{chunk_text}"

    resp = await llm.ainvoke([
        SystemMessage(content=LICENSE_CHECK_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    return resp.content.strip()


VULN_SCAN_SYSTEM_PROMPT = """\
You are CodeSense, an expert CVE and vulnerability analysis AI with up-to-date knowledge of security advisories.

You will receive dependency manifest files from a repository. Use your training knowledge of known CVEs and security advisories to identify vulnerable package versions.

Output EXACTLY in this format:

## Summary
- Ecosystems detected: <list>
- Dependencies reviewed: <N>
- Vulnerabilities found: <N> (Critical: <N> | High: <N> | Medium: <N> | Low: <N>)

---

## Vulnerabilities

### [CVE-001] <CVE-ID or descriptive title>
| Field | Value |
|---|---|
| Severity | CRITICAL / HIGH / MEDIUM / LOW |
| Package | package@version |
| Fixed in | <version> or "no fix available" |
| CVSS | <score> or "N/A" |

**Impact**: One sentence describing what the vulnerability allows an attacker to do.
**Action**: Upgrade to X.Y.Z or apply workaround Y.

---

(Repeat ### [CVE-002] for each vulnerability. If no known CVEs found, write "## No known vulnerabilities detected.")

STRICT RULES:
- Output ONLY the markdown above. No greetings, no sign-offs.
- Use your knowledge of real CVEs (e.g. express, react, vite, axios, lodash, minimist, etc. have well-known CVEs).
- Include the actual CVE ID when known (CVE-YYYY-NNNNN format).
- Only flag dependencies that appear in the manifest with versions you recognise as vulnerable.
- Do NOT hallucinate CVEs — if you are not confident a CVE affects a specific version range, skip it.
"""


async def _run_vuln_scan(chunks: list[dict], repo_url: str) -> str:
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage
    try:
        llm = get_fallback_llm(temperature=0.0)
    except RuntimeError:
        llm = get_llm(temperature=0.0)

    repo_name = repo_url.rstrip("/").removesuffix(".git").split("/")[-1] if repo_url else "repo"

    chunk_text_parts = []
    for c in chunks:
        chunk_text_parts.append(f"### {c['file']}\n```\n{c['content'][:2000]}\n```")
    chunk_text = "\n\n".join(chunk_text_parts)

    human_msg = f"Repository: {repo_name}\nManifest files ({len(chunks)} total):\n\n{chunk_text}"

    resp = await llm.ainvoke([
        SystemMessage(content=VULN_SCAN_SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    return resp.content.strip()


async def llm_reasoner_node(state: AgentState) -> AgentState:
    """Call the LLM over assembled context to produce findings."""
    from app.core.llm import get_fallback_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    # Bug scan uses per-chunk RAG pipeline
    if state.user_story == "bug_scan":
        chunks = state.tool_outputs.get("code_chunks", [])
        rag_ctx = "\n\n".join(
            f"[{c.repo_name}/{c.file_path}:{c.start_line}]\n{c.content[:300]}"
            for c in state.rag_results[:5]
        )
        if chunks:
            state.llm_reasoning = await _run_chunk_scan(chunks, rag_ctx)
            return state

    # Explain code uses full-repo chunk scan
    if state.user_story == "explain_code":
        chunks = state.tool_outputs.get("code_chunks", [])
        if chunks:
            state.llm_reasoning = await _run_explain_scan(chunks, state.raw_request.get("repo", ""))
            return state

    # Refactor uses full-repo chunk scan
    if state.user_story == "refactor":
        chunks = state.tool_outputs.get("code_chunks", [])
        if chunks:
            repo_url = (state.raw_request.get("repos") or [""])[0]
            state.llm_reasoning = await _run_refactor_scan(chunks, repo_url)
            return state

    # Vuln scan uses manifest files
    if state.user_story == "vuln_scan":
        chunks = state.tool_outputs.get("code_chunks", [])
        if chunks:
            state.llm_reasoning = await _run_vuln_scan(chunks, state.raw_request.get("repo", ""))
            return state

    # License check uses license files + manifests
    if state.user_story == "license_check":
        chunks = state.tool_outputs.get("code_chunks", [])
        if chunks:
            state.llm_reasoning = await _run_license_check_scan(chunks, state.raw_request.get("repos", []))
            return state

    # Version bump uses full-repo chunk scan
    if state.user_story == "version_bump":
        chunks = state.tool_outputs.get("code_chunks", [])
        if chunks:
            state.llm_reasoning = await _run_version_bump_scan(chunks, state.raw_request.get("repos", []))
            return state

    # Impact analysis uses full-repo chunk scan
    if state.user_story == "impact_analysis":
        chunks = state.tool_outputs.get("code_chunks", [])
        if chunks:
            repo_url = (state.raw_request.get("repos") or [""])[0]
            state.llm_reasoning = await _run_impact_analysis_scan(chunks, repo_url)
            return state

    # Migration plan uses full-repo chunk scan
    if state.user_story == "migration_plan":
        chunks = state.tool_outputs.get("code_chunks", [])
        if chunks:
            state.llm_reasoning = await _run_migration_plan_scan(chunks, state.raw_request.get("repo", ""))
            return state

    # Generate tests uses full-repo chunk scan
    if state.user_story == "generate_tests":
        chunks = state.tool_outputs.get("code_chunks", [])
        if chunks:
            state.llm_reasoning = await _run_generate_tests_scan(chunks, state.raw_request.get("repo", ""))
            return state

    # Similar bugs uses full-repo chunk scan
    if state.user_story == "similar_bugs":
        chunks = state.tool_outputs.get("code_chunks", [])
        if chunks:
            repo_url = (state.raw_request.get("repos") or [""])[0]
            state.llm_reasoning = await _run_similar_bugs_scan(chunks, repo_url)
            return state

    # All other stories — single LLM call
    try:
        llm = get_fallback_llm(temperature=0.1)
    except RuntimeError:
        llm = get_llm(temperature=0.1)

    prompt = _build_prompt(state)
    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])
    state.llm_reasoning = response.content
    return state
