"""RAG retriever node — semantic search over Chroma DB."""
from app.agent.state import AgentState
from app.tools.code_retriever import retrieve


US_TOP_K = {
    "similar_bugs":   20,
    "refactor":       15,
    "pr_review":      10,
    "default":         8,
}


async def rag_retriever_node(state: AgentState) -> AgentState:
    """Retrieve semantically similar code chunks from the vector store."""
    req    = state.raw_request
    us     = state.user_story
    top_k  = US_TOP_K.get(us, US_TOP_K["default"])
    repos  = req.get("repos") or ([req["repo"]] if req.get("repo") else None)

    # Build query from request context
    query = _build_query(state)
    if not query:
        return state

    try:
        chunks = await retrieve(query=query, top_k=top_k, repo_filter=repos)
        state.rag_results = chunks
    except Exception as e:
        state.tool_outputs["rag_error"] = str(e)

    return state


def _build_query(state: AgentState) -> str:
    req = state.raw_request
    us  = state.user_story

    if us == "similar_bugs":
        return req.get("known_bug", "")
    if us == "pr_review":
        meta = state.tool_outputs.get("pr_meta", {})
        return f"PR: {meta.get('title', '')} {meta.get('description', '')}"
    if us in ("explain_code", "refactor"):
        return f"code in {req.get('target', '')} {req.get('goal', '')}"
    if us == "impact_analysis":
        return f"usage of {req.get('symbol', '')}"
    if us == "generate_tests":
        return f"tests for {req.get('target', '')}"
    if us == "bug_scan":
        return f"bugs in {req.get('scope', '')}"
    if us == "migration_plan":
        return f"migrate {req.get('component', '')} to {req.get('target_stack', '')}"
    if us in ("version_bump", "license_check", "vuln_scan"):
        return f"dependencies in {' '.join(req.get('repos', []))}"

    return str(req)
