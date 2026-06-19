"""Context fetcher node — gathers code context via tools."""
from app.agent.state import AgentState
from app.tools import ast_parser, file_reader, diff_fetcher, call_graph


async def context_fetcher_node(state: AgentState) -> AgentState:
    """Fetch code context based on the user story."""
    req = state.raw_request
    outputs: dict = state.tool_outputs.copy()

    us = state.user_story

    # ── PR Review ──────────────────────────────────────────────────
    if us == "pr_review":
        repo      = req.get("repo", "")
        pr_number = req.get("pr_number", 0)
        if repo and pr_number:
            diff = await diff_fetcher.fetch_pr_diff(repo, pr_number)
            meta = await diff_fetcher.fetch_pr_metadata(repo, pr_number)
            outputs["diff"]     = diff
            outputs["pr_meta"]  = meta

            # Parse changed files
            changed = meta.get("changed_files", [])
            parsed_files = []
            repo_name = repo.rstrip("/").split("/")[-1]
            for fp in changed[:10]:  # cap at 10 files
                try:
                    content = await file_reader.read_file(repo_name, fp)
                    parsed  = ast_parser.parse_file(fp, content)
                    parsed_files.append({
                        "file_path": fp,
                        "symbols":   [s.name for s in parsed.symbols],
                        "language":  parsed.language,
                    })
                except Exception:
                    pass
            outputs["parsed_files"] = parsed_files

    # ── Explain code ───────────────────────────────────────────────
    elif us == "explain_code":
        repo_name = req.get("repo", "").rstrip("/").split("/")[-1]
        target    = req.get("target", "")
        if repo_name and target:
            try:
                content = await file_reader.read_file(repo_name, target)
                parsed  = ast_parser.parse_file(target, content)
                graph   = await call_graph.resolve(
                    target.replace("/", ".").replace(".py", "").replace(".ts", ""),
                    repos=[repo_name],
                )
                outputs["file_content"]   = content[:8000]
                outputs["ast"]            = {
                    "symbols": [{"name": s.name, "kind": s.kind,
                                 "start": s.start_line, "end": s.end_line}
                                for s in parsed.symbols],
                    "imports": parsed.imports,
                    "language": parsed.language,
                }
                outputs["call_graph"] = {
                    "callers":      [{"file": c.file_path, "line": c.line} for c in graph.callers],
                    "implementors": [{"file": c.file_path, "line": c.line} for c in graph.implementors],
                }
            except Exception as e:
                outputs["error"] = str(e)

    # ── Impact analysis ────────────────────────────────────────────
    elif us == "impact_analysis":
        symbol = req.get("symbol", "")
        repos  = req.get("repos", [])
        if symbol:
            graph = await call_graph.resolve(symbol, repos=repos if repos else None)
            outputs["call_graph"] = {
                "symbol":       graph.symbol,
                "callers":      [{"repo": c.repo_name, "file": c.file_path,
                                  "line": c.line, "type": c.usage_type,
                                  "context": c.context}
                                 for c in graph.callers],
                "implementors": [{"repo": c.repo_name, "file": c.file_path,
                                  "line": c.line, "type": c.usage_type}
                                 for c in graph.implementors],
                "references":   [{"repo": c.repo_name, "file": c.file_path,
                                  "line": c.line}
                                 for c in graph.references],
            }

    state.tool_outputs = outputs
    return state
