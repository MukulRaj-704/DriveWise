"""Default reranker — BAAI/bge-reranker-base, a cross-encoder run locally."""
from __future__ import annotations

from threading import Lock

from app.core.exceptions import DriveWiseError
from app.reranker.base import BaseReranker, RerankCandidate, RerankResult


class BgeReranker(BaseReranker):
    _model_cache: dict[str, object] = {}
    _lock = Lock()

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self.model_name = model_name
        self._model = self._load_model(model_name)

    @classmethod
    def _load_model(cls, model_name: str):
        with cls._lock:
            if model_name not in cls._model_cache:
                try:
                    from sentence_transformers import CrossEncoder
                except ImportError as exc:  # pragma: no cover
                    raise DriveWiseError("sentence-transformers is not installed.") from exc
                cls._model_cache[model_name] = CrossEncoder(model_name)
            return cls._model_cache[model_name]

    def rerank(self, query: str, candidates: list[RerankCandidate], top_k: int) -> list[RerankResult]:
        if not candidates:
            return []

        pairs = [(query, c.text) for c in candidates]
        scores = self._model.predict(pairs)

        scored = [
            RerankResult(id=c.id, text=c.text, metadata=c.metadata, score=float(s))
            for c, s in zip(candidates, scores)
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]


class NoopReranker(BaseReranker):
    """Used when RERANKER=none — passes the vector-search order through unchanged."""

    def rerank(self, query: str, candidates: list[RerankCandidate], top_k: int) -> list[RerankResult]:
        return [RerankResult(id=c.id, text=c.text, metadata=c.metadata, score=0.0) for c in candidates[:top_k]]
