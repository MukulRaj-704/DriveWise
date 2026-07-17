"""Builds the grounded prompt sent to the LLM. This is the single place that
enforces the "answer ONLY from context" contract, so every provider gets the
same anti-hallucination instructions regardless of vendor."""
from __future__ import annotations

from app.rag.retriever import RetrievedChunk

SYSTEM_PROMPT = """You are DriveWise, an assistant that answers questions about cars STRICTLY \
using the brochure excerpts provided as context.

Rules you must always follow:
1. Use ONLY the information in the provided context. Never use prior knowledge about cars, \
brands, or specifications.
2. Do not invent, guess, or infer information that is not explicitly present in the context.
3. If the context does not contain the answer, respond exactly with: \
"I couldn't find this information in the uploaded brochure."
4. When you do answer, cite the page number(s) you used, e.g. "(Page 12)".
5. Keep answers concise, factual, and directly responsive to the question.
6. If different excerpts conflict, point out the discrepancy rather than picking one silently."""


def format_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        page = c.metadata.get("page_number", "unknown")
        section = c.metadata.get("section") or "General"
        car = c.metadata.get("car_name") or "Unknown model"
        parts.append(
            f"[Excerpt {i} | {car} | Section: {section} | Page: {page}]\n{c.text.strip()}"
        )
    return "\n\n".join(parts)


def build_user_prompt(question: str, chunks: list[RetrievedChunk], history: str | None = None) -> str:
    context = format_context(chunks)
    history_block = f"\nPrevious conversation (for context only, do not treat as source material):\n{history}\n" if history else ""

    return f"""Context (brochure excerpts):
---
{context}
---
{history_block}
Question: {question}

Answer using ONLY the context above. If the answer isn't in the context, say so exactly as instructed."""
