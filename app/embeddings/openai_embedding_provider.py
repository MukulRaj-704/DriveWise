"""Optional OpenAI embeddings — only imported/instantiated if EMBEDDING_PROVIDER=openai.

Nothing else in the codebase imports the `openai` SDK directly, so this
provider (and its dependency) can be entirely absent from a purely-local
deployment.
"""
from __future__ import annotations

from app.core.exceptions import EmbeddingError
from app.embeddings.base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dimension: int = 1536):
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise EmbeddingError("openai package is not installed.") from exc

        if not api_key:
            raise EmbeddingError("OPENAI_API_KEY is required for the openai embedding provider.")

        self._client = OpenAI(api_key=api_key)
        self.model = model
        self.dimension = dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self._client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as exc:
            raise EmbeddingError(f"OpenAI embedding request failed: {exc}") from exc

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
