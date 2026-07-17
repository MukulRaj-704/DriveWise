"""Default embedding provider — runs fully locally, no API key required.

Uses BAAI/bge-small-en-v1.5 by default. BGE models are trained to work best
with a query instruction prefix, which we apply only to queries (not
documents), matching the model card's recommendation.
"""
from __future__ import annotations

from threading import Lock

from app.core.exceptions import EmbeddingError
from app.embeddings.base import BaseEmbeddingProvider

_BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    _model_cache: dict[str, object] = {}
    _lock = Lock()

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", dimension: int = 384):
        self.model_name = model_name
        self.dimension = dimension
        self._model = self._load_model(model_name)

    @classmethod
    def _load_model(cls, model_name: str):
        with cls._lock:
            if model_name not in cls._model_cache:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError as exc:  # pragma: no cover
                    raise EmbeddingError("sentence-transformers is not installed.") from exc
                cls._model_cache[model_name] = SentenceTransformer(model_name)
            return cls._model_cache[model_name]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            vectors = self._model.encode(
                texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False
            )
            return vectors.tolist()
        except Exception as exc:
            raise EmbeddingError(f"Failed to embed documents: {exc}") from exc

    def embed_query(self, text: str) -> list[float]:
        try:
            prefixed = f"{_BGE_QUERY_INSTRUCTION}{text}"
            vector = self._model.encode(prefixed, normalize_embeddings=True)
            return vector.tolist()
        except Exception as exc:
            raise EmbeddingError(f"Failed to embed query: {exc}") from exc
