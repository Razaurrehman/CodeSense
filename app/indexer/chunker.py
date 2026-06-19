"""AST-aware chunker — splits files at function/class boundaries."""
from __future__ import annotations
from app.tools.ast_parser import ASTSymbol


def chunk_file(
    content:     str,
    file_path:   str,
    language:    str,
    symbols:     list[ASTSymbol],
    max_tokens:  int = 400,
    overlap:     int = 50,
) -> list[dict]:
    """
    Chunk a source file at AST boundaries (function/class level).

    Falls back to line-based chunking when no symbols are available.

    Returns:
        List of dicts: {content, file_path, start_line, end_line,
                        symbol_name, chunk_type}
    """
    lines = content.splitlines()

    if not symbols:
        return _line_chunks(lines, file_path, max_tokens, overlap)

    chunks = []
    used_lines: set[int] = set()

    for sym in symbols:
        start = sym.start_line
        end   = sym.end_line
        chunk_lines = lines[start - 1: end]

        # If too large, split into sub-chunks
        if len(chunk_lines) > max_tokens:
            sub = _line_chunks(
                chunk_lines, file_path, max_tokens, overlap,
                line_offset=start - 1,
            )
            for s in sub:
                s["symbol_name"] = sym.name
                s["chunk_type"]  = sym.kind
            chunks.extend(sub)
        else:
            chunks.append({
                "content":     "\n".join(chunk_lines),
                "file_path":   file_path,
                "start_line":  start,
                "end_line":    end,
                "symbol_name": sym.name,
                "chunk_type":  sym.kind,
            })
        used_lines.update(range(start, end + 1))

    # Include module-level code not covered by symbols
    remaining = [
        (i + 1, line) for i, line in enumerate(lines)
        if (i + 1) not in used_lines and line.strip()
    ]
    if remaining:
        module_lines = [l for _, l in remaining]
        mod_chunks   = _line_chunks(module_lines, file_path, max_tokens, overlap)
        for c in mod_chunks:
            c["chunk_type"] = "module"
        chunks.extend(mod_chunks)

    return chunks


def _line_chunks(
    lines:       list[str],
    file_path:   str,
    max_tokens:  int,
    overlap:     int,
    line_offset: int = 0,
) -> list[dict]:
    """Simple sliding window chunker over lines."""
    chunks = []
    step   = max(1, max_tokens - overlap)
    i      = 0
    while i < len(lines):
        window = lines[i: i + max_tokens]
        chunks.append({
            "content":     "\n".join(window),
            "file_path":   file_path,
            "start_line":  line_offset + i + 1,
            "end_line":    line_offset + i + len(window),
            "symbol_name": "",
            "chunk_type":  "module",
        })
        i += step
    return chunks
