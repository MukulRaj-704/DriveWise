"""Reranker abstraction — re-scores an initial vector-search shortlist with a
cross-encoder for much higher precision than embedding similarity alone."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RerankCandidate:
    id: str
    text: str
    metadata: dict


@dataclass
class RerankResult:
    id: str
    text: str
    metadata: dict
    score: float


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, candidates: list[RerankCandidate], top_k: int) -> list[RerankResult]:
        raise NotImplementedError
