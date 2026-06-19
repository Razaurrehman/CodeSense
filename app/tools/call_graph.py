"""Symbol dependency graph — cross-repo caller/callee resolution."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from app.tools.code_retriever import retrieve
from app.agent.state import CodeChunk


@dataclass
class CallSite:
    repo_name:   str
    file_path:   str
    line:        int
    usage_type:  str   # DirectCall | Implementation | Reflection | Mock | Indirect
    context:     str   = ""


@dataclass
class CallGraphResult:
    symbol:      str
    callers:     list[CallSite] = field(default_factory=list)
    implementors:list[CallSite] = field(default_factory=list)
    references:  list[CallSite] = field(default_factory=list)


async def resolve(
    symbol: str,
    repos: list[str] | None = None,
) -> CallGraphResult:
    """
    Find all callers, implementors, and references of a symbol.

    Uses RAG semantic search over the indexed codebase.
    For production, swap with Sourcetrail HTTP API.

    Args:
        symbol: Fully qualified symbol name.
        repos:  Optional repo filter.

    Returns:
        CallGraphResult with all usage sites.
    """
    result = CallGraphResult(symbol=symbol)

    # Semantic search for the symbol name across the codebase
    chunks = await retrieve(
        query=f"usage of {symbol}",
        top_k=20,
        threshold=0.65,
        repo_filter=repos,
    )

    sym_short = symbol.split(".")[-1]  # last segment of FQN

    for chunk in chunks:
        usage_type = _classify_usage(chunk, symbol, sym_short)
        site = CallSite(
            repo_name=chunk.repo_name,
            file_path=chunk.file_path,
            line=chunk.start_line,
            usage_type=usage_type,
            context=chunk.content[:200],
        )
        if usage_type == "Implementation":
            result.implementors.append(site)
        elif usage_type in ("DirectCall", "Indirect"):
            result.callers.append(site)
        else:
            result.references.append(site)

    return result


def _classify_usage(chunk: CodeChunk, fqn: str, short: str) -> str:
    text = chunk.content
    if re.search(rf"\bclass\b.+\b{re.escape(short)}\b", text):
        return "Implementation"
    if re.search(rf"\b{re.escape(short)}\s*\(", text):
        return "DirectCall"
    if "reflect" in text.lower() or "getattr" in text.lower():
        return "Reflection"
    if "mock" in text.lower() or "patch" in text.lower():
        return "Mock"
    if short in text:
        return "Indirect"
    return "Reference"
