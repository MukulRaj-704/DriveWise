"""Formats the final answer + source attribution returned to the API layer."""
from __future__ import annotations

from app.rag.retriever import RetrievedChunk
from app.schemas.schemas import SourceAttribution

NOT_FOUND_MESSAGE = "I couldn't find this information in the uploaded brochure."


def format_response(answer: str, chunks: list[RetrievedChunk], brochure_names: dict[str, str]) -> tuple[str, list[SourceAttribution]]:
    """Returns (answer, sources). Sources are omitted when the model reports no answer found,
    since citing pages for a "not found" response would be misleading."""
    cleaned = answer.strip() or NOT_FOUND_MESSAGE

    if NOT_FOUND_MESSAGE.lower() in cleaned.lower():
        return cleaned, []

    sources = [
        SourceAttribution(
            chunk_id=c.chunk_id,
            brochure_id=c.metadata.get("brochure_id", ""),
            brochure_name=brochure_names.get(c.metadata.get("brochure_id", ""), "Unknown brochure"),
            page=c.metadata.get("page_number"),
            section=c.metadata.get("section"),
        )
        for c in chunks
    ]
    # De-duplicate sources that point at the same page/section of the same brochure.
    seen: set[tuple] = set()
    deduped: list[SourceAttribution] = []
    for s in sources:
        key = (s.brochure_id, s.page, s.section)
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    return cleaned, deduped
