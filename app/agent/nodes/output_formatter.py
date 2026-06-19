"""Output formatter node — wraps LLM reasoning in the correct Section D template."""
from datetime import datetime
from app.agent.state import AgentState


def _ts() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


async def output_formatter_node(state: AgentState) -> AgentState:
    """
    Apply the structured header and footer for the identified user story.
    The LLM reasoning content is embedded as the body.
    """
    us  = state.user_story
    req = state.raw_request
    body = state.llm_reasoning.strip()

    header = _build_header(us, req)
    footer = "\n\n── NEXT STEPS ────────────────────────────────────────────────────\n" \
             "□ Review the findings above and address items marked CRITICAL or HIGH first.\n" \
             "□ Confirm or suppress findings via POST /api/v1/feedback.\n"

    state.final_output = f"{header}\n\n{body}{footer}"
    return state


def _build_header(us: str, req: dict) -> str:
    ts = _ts()
    headers = {
        "pr_review": (
            f"[AI Review] Pull Request #{req.get('pr_number', '?')} — "
            f"{req.get('repo', '').split('/')[-1]}\n"
            f"Generated: {ts}"
        ),
        "bug_scan": (
            f"Bug Detection Report — {req.get('repo', req.get('scope', ''))}\n"
            f"Scope    : {req.get('scope', 'repo-wide')}\n"
            f"Generated: {ts}"
        ),
        "explain_code": (
            f"Code Explanation — {req.get('target', '')}\n"
            f"Repo     : {req.get('repo', '')}\n"
            f"Generated: {ts}"
        ),
        "refactor": (
            f"Refactoring Proposal — {req.get('target', '')}\n"
            f"Goal     : {req.get('goal', '')}\n"
            f"Generated: {ts}"
        ),
        "similar_bugs": (
            f"Similar Bug Detection Report\n"
            f"Repos    : {', '.join(req.get('repos', []))}\n"
            f"Generated: {ts}"
        ),
        "generate_tests": (
            f"Test Generation Report — {req.get('target', '')}\n"
            f"Framework: {req.get('framework', 'auto-detect')}\n"
            f"Generated: {ts}"
        ),
        "migration_plan": (
            f"Migration Plan — {req.get('component', '')}\n"
            f"From     : (current)\n"
            f"To       : {req.get('target_stack', '')}\n"
            f"Generated: {ts}"
        ),
        "impact_analysis": (
            f"Impact Analysis — {req.get('symbol', '')}\n"
            f"Proposed : {req.get('proposed_change', '')}\n"
            f"Repos    : {', '.join(req.get('repos', []))}\n"
            f"Generated: {ts}"
        ),
        "version_bump": (
            f"Dependency Update Report\n"
            f"Repos    : {', '.join(req.get('repos', []))}\n"
            f"Ecosystem: {req.get('ecosystem', 'all')}\n"
            f"Generated: {ts}"
        ),
        "license_check": (
            f"License Compliance Report\n"
            f"Project  : {req.get('project_type', 'commercial')}\n"
            f"Repos    : {', '.join(req.get('repos', []))}\n"
            f"Generated: {ts}"
        ),
        "vuln_scan": (
            f"Vulnerability Report\n"
            f"Repos    : {', '.join(req.get('repos', []))}\n"
            f"Generated: {ts}"
        ),
    }
    return headers.get(us, f"CodeSense Report — {us}\nGenerated: {ts}")
