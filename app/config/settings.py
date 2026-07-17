"""
Central configuration for DriveWise.

Every tunable knob (which LLM provider, which embedding model, which
vector store, secrets, etc.) is read from the environment. Nothing in
the rest of the codebase should read `os.environ` directly — always
go through `get_settings()` so there is a single source of truth and
so tests can override settings easily.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "DriveWise"
    APP_ENV: Literal["development", "production", "test"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Security / Auth ---
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://drivewise:drivewise@localhost:5432/drivewise"

    # --- Storage ---
    STORAGE_PROVIDER: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_PATH: str = "storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 25

    # --- PDF Parser ---
    PDF_PARSER: Literal["pymupdf", "pdfplumber"] = "pymupdf"

    # --- Chunking ---
    CHUNK_MAX_TOKENS: int = 400
    CHUNK_OVERLAP_TOKENS: int = 60

    # --- Embeddings ---
    EMBEDDING_PROVIDER: Literal["sentence_transformers", "openai"] = "sentence_transformers"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIMENSION: int = 384

    # --- Vector Store ---
    VECTOR_DB: Literal["faiss", "chroma"] = "faiss"
    FAISS_INDEX_PATH: str = "storage/vectors/faiss_index"
    CHROMA_PERSIST_DIR: str = "storage/vectors/chroma"

    # --- Reranker ---
    RERANKER: Literal["bge", "none"] = "bge"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    RERANK_TOP_K: int = 5
    RETRIEVAL_TOP_K: int = 20

    # --- LLM ---
    # Primary provider. In development this is typically "ollama" (free, fully
    # local, no rate limits). In production it's typically a hosted provider.
    LLM_PROVIDER: Literal["ollama", "openai", "gemini", "groq"] = "ollama"

    # Ordered fallback chain: if the primary provider fails (rate limit, outage,
    # timeout, etc.) DriveWise automatically retries with the next provider in
    # this list before giving up. Example for production: LLM_PROVIDER=groq
    # with LLM_FALLBACK_PROVIDERS=gemini means "use Groq's free tier, and if it
    # gets rate-limited, fall back to Gemini's free tier automatically."
    # Leave empty (the default) to disable fallback entirely, which is the
    # right choice for local development against Ollama.
    LLM_FALLBACK_PROVIDERS: list[Literal["ollama", "openai", "gemini", "groq"]] = []

    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"

    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (env is read once per process)."""
    return Settings()
