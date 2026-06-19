"""Clarifier node — asks one targeted question when intent is unclear."""
from app.agent.state import AgentState


async def clarifier_node(state: AgentState) -> AgentState:
    """Return the clarification question as the final output."""
    state.final_output = (
        "❓ **Clarification needed**\n\n"
        + state.clarification_question
    )
    return state
