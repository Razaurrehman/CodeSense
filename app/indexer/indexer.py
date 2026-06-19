"""Main indexing pipeline — clones repos, chunks, embeds, stores in Chroma."""
from __future__ import annotations
import asyncio
from pathlib import Path
from datetime import datetime
import yaml

import chromadb
from app.core.config import settings
from app.core.llm import get_embeddings
from app.indexer.chunker import chunk_file
from app.tools.ast_parser import parse_file, _detect_language
import structlog

log = structlog.get_logger()


async def index_repo(repo_cfg: dict) -> dict:
    """
    Index a single repository into Chroma DB.

    Args:
        repo_cfg: Entry from repos.yaml.

    Returns:
        Status dict with file_count and chunk_count.
    """
    repo_name = repo_cfg["name"]
    repo_url  = repo_cfg["url"]
    branch    = repo_cfg.get("branch", "main")
    local     = Path("/repos") / repo_name

    log.info("Indexing repo", repo=repo_name)

    # Clone / pull
    await _clone_or_pull(repo_url, branch, local)

    # Collect source files
    source_files = _collect_files(local, repo_cfg.get("language", ""))

    # Get Chroma collection
    client     = chromadb.AsyncHttpClient(host=settings.chroma_host, port=settings.chroma_port)
    collection = await client.get_or_create_collection(
        settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )
    embeddings = get_embeddings()

    file_count  = 0
    chunk_count = 0

    for file_path in source_files:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            language = _detect_language(str(file_path))
            parsed   = parse_file(str(file_path), content)
            chunks   = chunk_file(
                content=content,
                file_path=str(file_path.relative_to(local)),
                language=language,
                symbols=parsed.symbols,
            )

            if not chunks:
                continue

            texts    = [c["content"] for c in chunks]
            embs     = embeddings.embed_documents(texts)
            ids      = [f"{repo_name}::{c['file_path']}::{c['start_line']}" for c in chunks]
            metadatas = [
                {
                    "repo_name":   repo_name,
                    "file_path":   c["file_path"],
                    "start_line":  c["start_line"],
                    "end_line":    c["end_line"],
                    "language":    language,
                    "symbol_name": c.get("symbol_name", ""),
                    "chunk_type":  c.get("chunk_type", ""),
                }
                for c in chunks
            ]

            await collection.upsert(
                ids=ids,
                embeddings=embs,
                documents=texts,
                metadatas=metadatas,
            )

            file_count  += 1
            chunk_count += len(chunks)
        except Exception as e:
            log.warning("Failed to index file", file=str(file_path), error=str(e))

    log.info("Indexing complete", repo=repo_name, files=file_count, chunks=chunk_count)
    return {"repo_name": repo_name, "file_count": file_count, "chunk_count": chunk_count}


async def index_all() -> list[dict]:
    """Index all repositories from repos.yaml."""
    config_path = Path(settings.repos_config_path)
    if not config_path.exists():
        return []

    repos  = yaml.safe_load(config_path.read_text()).get("repos", [])
    tasks  = [index_repo(r) for r in repos]
    return await asyncio.gather(*tasks)


def _collect_files(root: Path, language: str) -> list[Path]:
    EXTENSIONS = {
        "python":     [".py"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx"],
        "csharp":     [".cs"],
        "go":         [".go"],
    }
    exts = EXTENSIONS.get(language, [".py", ".ts", ".tsx", ".js", ".jsx", ".cs", ".go"])
    files = []
    for ext in exts:
        files.extend(root.rglob(f"*{ext}"))
    # Skip node_modules, .git, dist, build
    skip = {"node_modules", ".git", "dist", "build", "__pycache__", ".venv"}
    return [f for f in files if not any(p in f.parts for p in skip)]


async def _clone_or_pull(url: str, branch: str, local: Path):
    import subprocess
    if (local / ".git").exists():
        proc = await asyncio.create_subprocess_exec(
            "git", "-C", str(local), "pull", "origin", branch,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
    else:
        local.parent.mkdir(parents=True, exist_ok=True)
        token = settings.git_token
        auth_url = url.replace("https://", f"https://oauth2:{token}@") if token else url
        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--branch", branch, "--depth", "1", auth_url, str(local),
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
