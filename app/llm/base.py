"""LLM provider abstraction. The RAG pipeline (app/rag/*) must depend ONLY on
this interface — never on a specific vendor SDK — so any provider can be
swapped in purely via configuration."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Return the full completion for `prompt`."""
        raise NotImplementedError

    @abstractmethod
    async def stream(self, prompt: str, system_prompt: str | None = None) -> AsyncIterator[str]:
        """Yield the completion incrementally, token/chunk by token/chunk."""
        raise NotImplementedError
        yield  # pragma: no cover - makes this an async generator for type checkers
