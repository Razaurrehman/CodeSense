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
        repo = req.get("repo", "")
        if not repo:
            state.tool_outputs = outputs
            return state

        repo_name = repo.rstrip("/").removesuffix(".git").split("/")[-1]

        # Fetch all open PRs (up to 5)
        try:
            open_prs = await diff_fetcher.list_open_prs(repo, limit=5)
        except Exception:
            open_prs = []

        if not open_prs:
            outputs["pr_meta"] = {"error": "No open pull requests found."}
            outputs["diff"]    = ""
            outputs["parsed_files"] = []
            state.tool_outputs = outputs
            return state

        all_pr_data = []
        for pr in open_prs:
            pr_number = pr["number"]
            try:
                diff = await diff_fetcher.fetch_pr_diff(repo, pr_number)
                meta = await diff_fetcher.fetch_pr_metadata(repo, pr_number)

                # Parse up to 5 changed files per PR
                parsed_files = []
                for fp in meta.get("changed_files", [])[:5]:
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

                all_pr_data.append({
                    "number":       pr_number,
                    "title":        pr["title"],
                    "author":       pr["author"],
                    "url":          pr["url"],
                    "meta":         meta,
                    "diff":         diff[:2000],
                    "parsed_files": parsed_files,
                })
            except Exception:
                all_pr_data.append({
                    "number": pr_number,
                    "title":  pr["title"],
                    "author": pr["author"],
                    "url":    pr["url"],
                    "error":  "Failed to fetch diff",
                })

        outputs["all_prs"]      = all_pr_data
        outputs["pr_meta"]      = {"total_open": len(open_prs)}
        outputs["diff"]         = "\n\n".join(
            f"--- PR #{p['number']}: {p['title']} ---\n{p.get('diff','')}"
            for p in all_pr_data
        )[:4000]
        outputs["parsed_files"] = [
            f for p in all_pr_data for f in p.get("parsed_files", [])
        ]

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
