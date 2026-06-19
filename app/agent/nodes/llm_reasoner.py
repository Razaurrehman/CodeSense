"""LLM reasoner node — synthesises all context into findings."""
from __future__ import annotations
import json
from app.agent.state import AgentState
from app.core.llm import get_llm

SYSTEM_PROMPT = """\
You are CodeSense, an AI-powered Code Intelligence Agent for professional engineering teams.

RULES:
- Be precise and evidence-based. Cite file paths and line numbers.
- Never fabricate symbols, CVE IDs, or line numbers.
- Label uncertain findings: [VERIFY], [INFERRED], or [POSSIBLE].
- You are a PROPOSAL ENGINE — never suggest applying changes directly.
- Be concise. Use structured output. No prose essays.
"""

TASK_PROMPTS: dict[str, str] = {

"pr_review": """\
Perform a thorough PR review based on the diff and parsed files provided.
Analyse: logic correctness, security issues, naming, test coverage, edge cases.
Output per the PR Review format (Section D US-1).

PR Metadata: {pr_meta}
Changed files and symbols: {parsed_files}
RAG similar patterns: {rag_context}
Static analysis findings: {static_findings}
Diff (first 4000 chars): {diff}
""",

"bug_scan": """\
Analyse the static analysis findings and RAG context to identify real bugs.
Filter false positives. Add semantic bugs the static analyser missed.
Output per the Bug Detection Report format (Section D US-2).

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
Generate the webhook alert payload for findings above threshold.
Output per the Vulnerability Report format (Section D US-11).

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


async def llm_reasoner_node(state: AgentState) -> AgentState:
    """Call the LLM over assembled context to produce findings."""
    llm    = get_llm(temperature=0.1)
    prompt = _build_prompt(state)

    from langchain_core.messages import SystemMessage, HumanMessage
    response = await llm.ainvoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ])

    state.llm_reasoning = response.content
    return state
