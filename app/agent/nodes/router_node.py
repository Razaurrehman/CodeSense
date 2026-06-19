"""Router node — classifies intent into one of 11 user stories."""
from app.agent.state import AgentState
from app.core.llm import get_llm

USER_STORIES = {
    "pr_review":       "Review a pull request",
    "bug_scan":        "Detect bugs in existing code",
    "explain_code":    "Explain legacy or unfamiliar code",
    "refactor":        "Suggest refactoring across repos",
    "similar_bugs":    "Find similar bugs to a known defect",
    "generate_tests":  "Generate unit/integration tests",
    "migration_plan":  "Plan migration of a legacy component",
    "impact_analysis": "Analyse impact of changing a symbol/interface",
    "version_bump":    "Propose safe library version upgrades",
    "license_check":   "Verify open-source license compliance",
    "vuln_scan":       "Detect CVEs and vulnerabilities",
}

ROUTER_PROMPT = """\
You are a routing agent for a code intelligence system. Classify the user's request
into exactly one of these user stories:

{stories}

If the user_story field is already set in the request JSON, confirm it.
If it is missing or ambiguous, classify from the raw request.

Respond with ONLY the user_story key (e.g. "pr_review").
If truly ambiguous, respond with "UNCLEAR".

Request:
{request}
"""


async def router_node(state: AgentState) -> AgentState:
    """Classify intent → set state.user_story."""
    # If already provided and valid, trust it
    if state.user_story and state.user_story in USER_STORIES:
        return state

    llm = get_llm(temperature=0)
    stories_text = "\n".join(f"  {k}: {v}" for k, v in USER_STORIES.items())

    response = await llm.ainvoke(
        ROUTER_PROMPT.format(
            stories=stories_text,
            request=str(state.raw_request),
        )
    )
    classified = response.content.strip().lower().replace('"', "").replace("'", "")

    if classified == "unclear" or classified not in USER_STORIES:
        state.clarification_needed = True
        state.clarification_question = (
            "I couldn't determine what you need. Please specify one of:\n"
            + "\n".join(f"• {k}: {v}" for k, v in USER_STORIES.items())
        )
    else:
        state.user_story = classified

    return state
