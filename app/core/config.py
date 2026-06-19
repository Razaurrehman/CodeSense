from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str    = "http://ollama:11434"
    ollama_model: str       = "codellama:34b"
    ollama_embed_model: str = "nomic-embed-text"

    # Chroma
    chroma_host: str       = "chromadb"
    chroma_port: int       = 8000
    chroma_collection: str = "codebase_index"

    # Postgres
    postgres_url: str = "postgresql+asyncpg://codeagent:codeagent@postgres:5432/codeagent"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Git
    git_token: str = ""

    # Optional
    groq_api_key: str      = ""
    alert_webhook_url: str = ""

    # App
    repos_config_path: str = "/config/repos.yaml"
    log_level: str         = "INFO"

    # RAG
    rag_top_k: int                  = 8
    rag_similarity_threshold: float = 0.72
    chunk_size_tokens: int          = 400
    chunk_overlap_tokens: int       = 50

    class Config:
        env_file = ".env"
        extra    = "ignore"


settings = Settings()
