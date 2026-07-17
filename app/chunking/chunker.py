"""Semantic chunking.

Strategy: walk the parsed blocks in document order, accumulating text under
the current heading until the token budget (CHUNK_MAX_TOKENS) is reached,
then close the chunk and start a new one that re-includes the last
CHUNK_OVERLAP_TOKENS worth of text for continuity. Headings always start a
fresh accumulation boundary preference (we prefer to break on heading
changes rather than mid-thought, but we still respect the max size within
one heading).

A very rough tokenizer (whitespace split) is used to keep this dependency-free;
swap in a real tokenizer if exact token counts ever matter.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.parser.base import ParsedBlock


def _token_count(text: str) -> int:
    return len(text.split())


@dataclass
class SemanticChunk:
    chunk_id: str
    text: str
    page_number: int | None
    section: str | None
    chunk_index: int
    metadata: dict = field(default_factory=dict)


class SemanticChunker:
    def __init__(self, max_tokens: int = 400, overlap_tokens: int = 60):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, blocks: list[ParsedBlock], extra_metadata: dict | None = None) -> list[SemanticChunk]:
        extra_metadata = extra_metadata or {}
        chunks: list[SemanticChunk] = []

        buffer_lines: list[str] = []
        buffer_tokens = 0
        chunk_start_page: int | None = None
        current_section: str | None = None
        chunk_index = 0

        def flush() -> None:
            nonlocal buffer_lines, buffer_tokens, chunk_start_page, chunk_index
            if not buffer_lines:
                return
            text = "\n".join(buffer_lines).strip()
            if text:
                chunks.append(
                    SemanticChunk(
                        chunk_id=str(uuid.uuid4()),
                        text=text,
                        page_number=chunk_start_page,
                        section=current_section,
                        chunk_index=chunk_index,
                        metadata=dict(extra_metadata),
                    )
                )
                chunk_index += 1

            # carry overlap into the next chunk
            overlap_lines: list[str] = []
            overlap_tok = 0
            for line in reversed(buffer_lines):
                t = _token_count(line)
                if overlap_tok + t > self.overlap_tokens:
                    break
                overlap_lines.insert(0, line)
                overlap_tok += t
            buffer_lines = overlap_lines
            buffer_tokens = overlap_tok

        for block in blocks:
            if block.block_type == "heading":
                # Heading change: close current chunk (unless empty) to keep sections coherent.
                if buffer_tokens > 0:
                    flush()
                current_section = block.text
                chunk_start_page = block.page_number
                continue

            if chunk_start_page is None:
                chunk_start_page = block.page_number

            block_tokens = _token_count(block.text)
            if buffer_tokens + block_tokens > self.max_tokens and buffer_tokens > 0:
                flush()
                chunk_start_page = block.page_number

            buffer_lines.append(block.text)
            buffer_tokens += block_tokens

        flush()
        return chunks
