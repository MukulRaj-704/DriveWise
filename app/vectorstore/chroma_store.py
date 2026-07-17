"""Optional Chroma vector store — has native metadata filtering, useful once brochure
catalogs grow large enough that FAISS's over-fetch-and-filter approach gets wasteful.

Selected via VECTOR_DB=chroma.
"""
from __future__ import annotations

from app.core.exceptions import VectorStoreError
from app.vectorstore.base import BaseVectorStore, VectorRecord, VectorSearchResult


class ChromaVectorStore(BaseVectorStore):
    def __init__(self, persist_dir: str, collection_name: str = "drivewise_chunks"):
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover
            raise VectorStoreError("chromadb is not installed.") from exc

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def add(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        try:
            self._collection.upsert(
                ids=[r.id for r in records],
                embeddings=[r.vector for r in records],
                metadatas=[r.metadata for r in records],
            )
        except Exception as exc:
            raise VectorStoreError(f"Failed to add vectors: {exc}") from exc

    def search(
        self, query_vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[VectorSearchResult]:
        where = None
        if filters:
            clean = {k: v for k, v in filters.items() if v is not None}
            if clean:
                where = {k: {"$eq": v} for k, v in clean.items()} if len(clean) > 1 else clean

        try:
            result = self._collection.query(
                query_embeddings=[query_vector], n_results=top_k, where=where
            )
        except Exception as exc:
            raise VectorStoreError(f"Vector search failed: {exc}") from exc

        out: list[VectorSearchResult] = []
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        for _id, dist, meta in zip(ids, distances, metadatas):
            similarity = 1 - dist  # cosine distance -> similarity
            out.append(VectorSearchResult(id=_id, score=similarity, metadata=meta or {}))
        return out

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        try:
            self._collection.delete(ids=ids)
        except Exception as exc:
            raise VectorStoreError(f"Failed to delete vectors: {exc}") from exc

    def update(self, records: list[VectorRecord]) -> None:
        self.add(records)  # upsert already handles replace
