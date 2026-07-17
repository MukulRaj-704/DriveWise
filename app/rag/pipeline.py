"""Orchestrates the full RAG pipeline:

  question -> metadata filter -> vector search -> rerank -> prompt -> LLM -> format -> answer + sources

This module never imports a concrete provider SDK — only the abstract
interfaces (BaseLLMProvider, BaseEmbeddingProvider, BaseVectorStore,
BaseReranker) — so it works unchanged no matter which providers are wired
up via the factories.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.exceptions import NoRelevantContextError
from app.llm.base import BaseLLMProvider
from app.rag.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from app.rag.response_formatter import NOT_FOUND_MESSAGE, format_response
from app.rag.retriever import Retriever
from app.schemas.schemas import SourceAttribution


@dataclass
class RagResult:
    answer: str
    sources: list[SourceAttribution]


class RagPipeline:
    def __init__(self, retriever: Retriever, llm: BaseLLMProvider):
        self.retriever = retriever
        self.llm = llm

    async def answer(
        self,
        question: str,
        chunk_texts: dict[str, str],
        brochure_names: dict[str, str],
        filters: dict | None = None,
        history: str | None = None,
    ) -> RagResult:
        chunks = self.retriever.retrieve(question, chunk_texts, filters=filters)

        if not chunks:
            return RagResult(answer=NOT_FOUND_MESSAGE, sources=[])

        prompt = build_user_prompt(question, chunks, history=history)
        raw_answer = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)

        answer, sources = format_response(raw_answer, chunks, brochure_names)
        return RagResult(answer=answer, sources=sources)
