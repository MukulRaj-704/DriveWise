"""
Dependency-injection wiring.

Heavy providers (embedding model, reranker model, vector store, LLM client)
are expensive to construct, so they are built once as process-wide singletons
and handed out via FastAPI's `Depends`. Swapping any of them is a matter of
changing environment variables — nothing here hardcodes a vendor.
"""
from __future__ import annotations

from functools import lru_cache

from app.config.settings import Settings, get_settings
from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.factory import get_embedding_provider
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.parser.base import BasePDFParser
from app.parser.factory import get_pdf_parser
from app.rag.retriever import Retriever
from app.reranker.base import BaseReranker
from app.reranker.factory import get_reranker
from app.vectorstore.base import BaseVectorStore
from app.vectorstore.factory import get_vector_store


@lru_cache
def get_embedding_provider_singleton() -> BaseEmbeddingProvider:
    return get_embedding_provider(get_settings())


@lru_cache
def get_vector_store_singleton() -> BaseVectorStore:
    return get_vector_store(get_settings())


@lru_cache
def get_reranker_singleton() -> BaseReranker:
    return get_reranker(get_settings())


@lru_cache
def get_pdf_parser_singleton() -> BasePDFParser:
    return get_pdf_parser(get_settings())


def get_llm_provider_dependency() -> BaseLLMProvider:
    # Not cached: cheap to construct (just an HTTP client wrapper) and this
    # avoids stale API keys if settings change between requests in tests.
    return get_llm_provider(get_settings())


def get_retriever(settings: Settings | None = None) -> Retriever:
    settings = settings or get_settings()
    return Retriever(
        embedding_provider=get_embedding_provider_singleton(),
        vector_store=get_vector_store_singleton(),
        reranker=get_reranker_singleton(),
        retrieval_top_k=settings.RETRIEVAL_TOP_K,
        rerank_top_k=settings.RERANK_TOP_K,
    )
