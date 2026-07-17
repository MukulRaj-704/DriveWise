"""Vector store abstraction."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VectorRecord:
    id: str  # matches Chunk.id in the relational DB
    vector: list[float]
    metadata: dict  # brochure_id, car_name, page_number, section, etc. — used for filtering


@dataclass
class VectorSearchResult:
    id: str
    score: float
    metadata: dict


class BaseVectorStore(ABC):
    """Interface every vector store backend must implement."""

    @abstractmethod
    def add(self, records: list[VectorRecord]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self, query_vector: list[float], top_k: int, filters: dict | None = None
    ) -> list[VectorSearchResult]:
        """Return the top_k nearest vectors, optionally restricted by exact-match metadata filters."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, records: list[VectorRecord]) -> None:
        """Replace existing vectors/metadata for the given ids (delete + add)."""
        raise NotImplementedError
