from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.chat_models import ChatGroq
from app.core.config import settings


def get_llm(temperature: float = 0.1) -> ChatOllama:
    """Primary LLM — local Ollama."""
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        temperature=temperature,
        num_ctx=16000,
    )


def get_fallback_llm(temperature: float = 0.1):
    """Fallback LLM — Groq API (opt-in)."""
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY not set — cannot use fallback LLM")
    return ChatGroq(
        api_key=settings.groq_api_key,
        model="deepseek-r1-distill-llama-70b",
        temperature=temperature,
    )


def get_embeddings() -> OllamaEmbeddings:
    """Nomic embed via Ollama."""
    return OllamaEmbeddings(
        base_url=settings.ollama_base_url,
        model=settings.ollama_embed_model,
    )
