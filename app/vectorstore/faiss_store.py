"""Default vector store — FAISS, running fully in-process, persisted to disk.

FAISS has no native metadata filtering, so we do exact-match metadata
filtering ourselves: over-fetch candidates from the index, then filter by
metadata, expanding the search if needed. This is fine at brochure-catalog
scale (thousands to low millions of chunks); a managed vector DB with
native filtering (e.g. Chroma, pgvector, Pinecone) would be preferable at
much larger scale, which is exactly why this sits behind `BaseVectorStore`.
"""
from __future__ import annotations

import os
import pickle
import threading

import numpy as np

from app.core.exceptions import VectorStoreError
from app.vectorstore.base import BaseVectorStore, VectorRecord, VectorSearchResult


class FaissVectorStore(BaseVectorStore):
    def __init__(self, index_path: str, dimension: int):
        self.index_path = index_path
        self.dimension = dimension
        self._lock = threading.Lock()

        os.makedirs(os.path.dirname(index_path) or ".", exist_ok=True)

        try:
            import faiss
        except ImportError as exc:  # pragma: no cover
            raise VectorStoreError("faiss-cpu is not installed.") from exc
        self._faiss = faiss

        # int64 sequential key -> chunk uuid string, and uuid -> metadata
        self._int_to_uuid: dict[int, str] = {}
        self._uuid_to_int: dict[str, int] = {}
        self._metadata: dict[str, dict] = {}
        self._next_id = 0

        self._index = self._load_or_create()

    # ---------- persistence ----------

    def _meta_path(self) -> str:
        return f"{self.index_path}.meta.pkl"

    def _load_or_create(self):
        faiss = self._faiss
        if os.path.exists(self.index_path) and os.path.exists(self._meta_path()):
            index = faiss.read_index(self.index_path)
            with open(self._meta_path(), "rb") as f:
                state = pickle.load(f)
            self._int_to_uuid = state["int_to_uuid"]
            self._uuid_to_int = state["uuid_to_int"]
            self._metadata = state["metadata"]
            self._next_id = state["next_id"]
            return index

        base = faiss.IndexFlatIP(self.dimension)  # cosine sim, assuming normalized vectors
        return faiss.IndexIDMap2(base)

    def _persist(self) -> None:
        self._faiss.write_index(self._index, self.index_path)
        with open(self._meta_path(), "wb") as f:
            pickle.dump(
                {
                    "int_to_uuid": self._int_to_uuid,
                    "uuid_to_int": self._uuid_to_int,
                    "metadata": self._metadata,
                    "next_id": self._next_id,
                },
                f,
            )

    # ---------- interface ----------

    def add(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        with self._lock:
            ids = []
            vectors = []
            for r in records:
                int_id = self._next_id
                self._next_id += 1
                self._int_to_uuid[int_id] = r.id
                self._uuid_to_int[r.id] = int_id
                self._metadata[r.id] = r.metadata
                ids.append(int_id)
                vectors.append(r.vector)

            arr = np.array(vectors, dtype="float32")
            id_arr = np.array(ids, dtype="int64")
            try:
                self._index.add_with_ids(arr, id_arr)
            except Exception as exc:
                raise VectorStoreError(f"Failed to add vectors: {exc}") from exc
            self._persist()

    def search(
        self, query_vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[VectorSearchResult]:
        with self._lock:
            if self._index.ntotal == 0:
                return []

            query = np.array([query_vector], dtype="float32")

            # Over-fetch when filtering, expanding progressively if we don't have enough hits.
            fetch_k = top_k if not filters else min(self._index.ntotal, max(top_k * 5, 50))
            fetch_k = min(fetch_k, self._index.ntotal)

            try:
                scores, ids = self._index.search(query, fetch_k)
            except Exception as exc:
                raise VectorStoreError(f"Vector search failed: {exc}") from exc

            results: list[VectorSearchResult] = []
            for score, int_id in zip(scores[0], ids[0]):
                if int_id == -1:
                    continue
                uid = self._int_to_uuid.get(int(int_id))
                if uid is None:
                    continue
                meta = self._metadata.get(uid, {})
                if filters and not self._matches(meta, filters):
                    continue
                results.append(VectorSearchResult(id=uid, score=float(score), metadata=meta))
                if len(results) >= top_k:
                    break

            return results

    @staticmethod
    def _matches(metadata: dict, filters: dict) -> bool:
        for key, value in filters.items():
            if value is None:
                continue
            meta_value = metadata.get(key)
            if meta_value is None:
                return False
            if str(meta_value).strip().lower() != str(value).strip().lower():
                return False
        return True

    def delete(self, ids: list[str]) -> None:
        if not ids:
            return
        with self._lock:
            int_ids = [self._uuid_to_int[i] for i in ids if i in self._uuid_to_int]
            if not int_ids:
                return
            id_arr = np.array(int_ids, dtype="int64")
            try:
                self._index.remove_ids(id_arr)
            except Exception as exc:
                raise VectorStoreError(f"Failed to delete vectors: {exc}") from exc
            for uid in ids:
                int_id = self._uuid_to_int.pop(uid, None)
                if int_id is not None:
                    self._int_to_uuid.pop(int_id, None)
                self._metadata.pop(uid, None)
            self._persist()

    def update(self, records: list[VectorRecord]) -> None:
        self.delete([r.id for r in records])
        self.add(records)
