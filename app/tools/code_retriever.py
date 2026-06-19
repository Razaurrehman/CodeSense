"""Semantic search over Chroma DB vector store."""
from __future__ import annotations
import chromadb
from app.core.config import settings
from app.core.llm import get_embeddings
from app.agent.state import CodeChunk


_client: chromadb.AsyncHttpClient | None = None
_embeddings = None


def _get_client() -> chromadb.AsyncHttpClient:
    global _client
    if _client is None:
        _client = chromadb.AsyncHttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    return _client


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = get_embeddings()
    return _embeddings


async def retrieve(
    query: str,
    top_k: int = 8,
    threshold: float | None = None,
    repo_filter: list[str] | None = None,
) -> list[CodeChunk]:
    """
    Semantic search over the indexed codebase.

    Args:
        query:       Natural language query or code snippet.
        top_k:       Max results to return.
        threshold:   Minimum cosine similarity (defaults to settings value).
        repo_filter: Limit search to specific repos.

    Returns:
        Ranked list of CodeChunk objects.
    """
    if threshold is None:
        threshold = settings.rag_similarity_threshold

    client = _get_client()
    embeddings = _get_embeddings()

    query_embedding = embeddings.embed_query(query)

    collection = await client.get_collection(settings.chroma_collection)

    where = {"repo_name": {"$in": repo_filter}} if repo_filter else None

    results = await collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[CodeChunk] = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        score = 1.0 - dist  # convert distance → similarity
        if score < threshold:
            continue
        chunks.append(
            CodeChunk(
                repo_name=meta.get("repo_name", ""),
                file_path=meta.get("file_path", ""),
                start_line=int(meta.get("start_line", 0)),
                end_line=int(meta.get("end_line", 0)),
                content=doc,
                language=meta.get("language", ""),
                symbol_name=meta.get("symbol_name", ""),
                chunk_type=meta.get("chunk_type", ""),
                score=round(score, 4),
            )
        )

    return sorted(chunks, key=lambda c: c.score, reverse=True)
