"""Retrieval stage of the RAG pipeline: metadata-filtered vector search followed
by cross-encoder reranking. Depends only on the BaseVectorStore / BaseReranker /
BaseEmbeddingProvider interfaces — never a concrete vendor."""
from __future__ import annotations

from dataclasses import dataclass

from app.embeddings.base import BaseEmbeddingProvider
from app.reranker.base import BaseReranker, RerankCandidate
from app.vectorstore.base import BaseVectorStore


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict
    score: float


class Retriever:
    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        vector_store: BaseVectorStore,
        reranker: BaseReranker,
        retrieval_top_k: int = 20,
        rerank_top_k: int = 5,
    ):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.reranker = reranker
        self.retrieval_top_k = retrieval_top_k
        self.rerank_top_k = rerank_top_k

    def retrieve(
        self,
        query: str,
        chunk_texts: dict[str, str],
        filters: dict | None = None,
    ) -> list[RetrievedChunk]:
        """
        `chunk_texts` maps chunk_id -> full text, since the vector store only
        holds embeddings + light metadata, not the text itself (that lives in
        the relational DB / repository layer). This keeps the vector store
        swappable without needing to store full documents inside it.
        """
        query_vector = self.embedding_provider.embed_query(query)

        hits = self.vector_store.search(query_vector, top_k=self.retrieval_top_k, filters=filters)
        if not hits:
            return []

        candidates = [
            RerankCandidate(id=h.id, text=chunk_texts.get(h.id, ""), metadata=h.metadata)
            for h in hits
            if h.id in chunk_texts
        ]
        if not candidates:
            return []

        reranked = self.reranker.rerank(query, candidates, top_k=self.rerank_top_k)

        return [
            RetrievedChunk(chunk_id=r.id, text=r.text, metadata=r.metadata, score=r.score)
            for r in reranked
        ]
