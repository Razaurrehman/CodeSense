"""Tree-sitter AST parser for Python, TypeScript, JavaScript."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_typescript as tstypescript
    from tree_sitter import Language, Parser
    TS_AVAILABLE = True
except ImportError:
    TS_AVAILABLE = False


@dataclass
class ASTSymbol:
    name:        str
    kind:        str          # function | class | method | import
    start_line:  int
    end_line:    int
    text:        str          = ""
    children:    list["ASTSymbol"] = field(default_factory=list)


@dataclass
class ParseResult:
    file_path: str
    language:  str
    symbols:   list[ASTSymbol]
    imports:   list[str]
    raw_text:  str


def _detect_language(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return {
        ".py":  "python",
        ".ts":  "typescript",
        ".tsx": "typescript",
        ".js":  "javascript",
        ".jsx": "javascript",
    }.get(ext, "unknown")


def _get_parser(language: str) -> "Parser | None":
    if not TS_AVAILABLE:
        return None
    try:
        lang_map = {
            "python":     tspython.language(),
            "javascript": tsjavascript.language(),
            "typescript": tstypescript.language_typescript(),
        }
        if language not in lang_map:
            return None
        parser = Parser()
        parser.language = Language(lang_map[language])
        return parser
    except Exception:
        return None


def _extract_symbols_py(source: str) -> list[ASTSymbol]:
    """Regex fallback for Python when Tree-sitter unavailable."""
    symbols: list[ASTSymbol] = []
    lines = source.splitlines()
    for i, line in enumerate(lines, 1):
        m = re.match(r"^(class|def|async def)\s+(\w+)", line)
        if m:
            kind = "class" if m.group(1) == "class" else "function"
            symbols.append(ASTSymbol(name=m.group(2), kind=kind, start_line=i, end_line=i))
    return symbols


def _extract_imports_py(source: str) -> list[str]:
    imports = []
    for line in source.splitlines():
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            imports.append(line)
    return imports


def parse_file(file_path: str, content: str | None = None) -> ParseResult:
    """
    Parse a source file and extract its AST structure.

    Args:
        file_path: Path to the file (used for language detection).
        content:   Raw file content. If None, reads from disk.

    Returns:
        ParseResult with symbols and imports.
    """
    if content is None:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")

    language = _detect_language(file_path)
    parser   = _get_parser(language)

    if parser is not None:
        tree    = parser.parse(bytes(content, "utf-8"))
        symbols = _walk_tree(tree.root_node, content, language)
        imports = _extract_imports_py(content) if language == "python" else []
    else:
        # Regex fallback
        symbols = _extract_symbols_py(content)
        imports = _extract_imports_py(content)

    return ParseResult(
        file_path=file_path,
        language=language,
        symbols=symbols,
        imports=imports,
        raw_text=content,
    )


def _walk_tree(node, source: str, language: str) -> list[ASTSymbol]:
    """Walk Tree-sitter AST and collect symbols."""
    symbols: list[ASTSymbol] = []
    FUNCTION_TYPES = {"function_definition", "function_declaration",
                      "method_definition", "arrow_function"}
    CLASS_TYPES    = {"class_definition", "class_declaration"}

    def recurse(n):
        if n.type in FUNCTION_TYPES | CLASS_TYPES:
            name_node = next(
                (c for c in n.children if c.type in ("identifier", "property_identifier")),
                None,
            )
            name = name_node.text.decode() if name_node else "<anonymous>"
            kind = "class" if n.type in CLASS_TYPES else "function"
            text = source[n.start_byte:n.end_byte]
            symbols.append(ASTSymbol(
                name=name,
                kind=kind,
                start_line=n.start_point[0] + 1,
                end_line=n.end_point[0] + 1,
                text=text[:500],  # truncate for memory
            ))
        for child in n.children:
            recurse(child)

    recurse(node)
    return symbols
