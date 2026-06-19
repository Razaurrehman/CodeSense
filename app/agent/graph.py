"""LangGraph StateGraph definition for CodeSense."""
from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent.nodes.router_node      import router_node
from app.agent.nodes.context_fetcher  import context_fetcher_node
from app.agent.nodes.rag_retriever    import rag_retriever_node
from app.agent.nodes.analyser         import analyser_node
from app.agent.nodes.llm_reasoner     import llm_reasoner_node
from app.agent.nodes.output_formatter import output_formatter_node
from app.agent.nodes.clarifier        import clarifier_node

# Stories that start with context_fetcher (need file/AST/diff context)
CONTEXT_FIRST = {"pr_review", "explain_code", "refactor",
                 "generate_tests", "migration_plan", "impact_analysis"}

# Stories that start with analyser (need static/vuln/license tools)
ANALYSER_FIRST = {"bug_scan", "similar_bugs", "version_bump",
                  "license_check", "vuln_scan"}


def _route_after_router(state: AgentState) -> str:
    if state.clarification_needed:
        return "clarifier"
    if state.user_story in CONTEXT_FIRST:
        return "context_fetcher"
    return "analyser"


def _route_after_analyser(state: AgentState) -> str:
    # similar_bugs and bug_scan benefit from RAG re-ranking
    if state.user_story in ("similar_bugs", "bug_scan"):
        return "rag_retriever"
    return "llm_reasoner"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────────
    graph.add_node("router",           router_node)
    graph.add_node("context_fetcher",  context_fetcher_node)
    graph.add_node("rag_retriever",    rag_retriever_node)
    graph.add_node("analyser",         analyser_node)
    graph.add_node("llm_reasoner",     llm_reasoner_node)
    graph.add_node("output_formatter", output_formatter_node)
    graph.add_node("clarifier",        clarifier_node)

    # ── Entry point ────────────────────────────────────────────────
    graph.set_entry_point("router")

    # ── Edges ──────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "router",
        _route_after_router,
        {
            "clarifier":       "clarifier",
            "context_fetcher": "context_fetcher",
            "analyser":        "analyser",
        },
    )

    # context_fetcher → rag_retriever (always augment with semantic context)
    graph.add_edge("context_fetcher", "rag_retriever")

    # rag_retriever → llm_reasoner
    graph.add_edge("rag_retriever", "llm_reasoner")

    # analyser → conditional (rag or llm)
    graph.add_conditional_edges(
        "analyser",
        _route_after_analyser,
        {
            "rag_retriever": "rag_retriever",
            "llm_reasoner":  "llm_reasoner",
        },
    )

    # llm_reasoner → output_formatter → END
    graph.add_edge("llm_reasoner",     "output_formatter")
    graph.add_edge("output_formatter", END)

    # clarifier → END (waits for developer response)
    graph.add_edge("clarifier", END)

    return graph


# Compile once at startup
compiled_graph = build_graph().compile()


async def run_agent(request: dict, session_history: list[dict] | None = None) -> str:
    """
    Run the CodeSense agent for a given request.

    Args:
        request:         Raw request dict (must have 'user_story' or inferrable intent).
        session_history: Prior turns in the current session.

    Returns:
        Final formatted output string.
    """
    initial_state = AgentState(
        user_story=request.get("user_story", ""),
        raw_request=request,
        session_history=session_history or [],
    )

    final_state = await compiled_graph.ainvoke(initial_state)
    return final_state.final_output
