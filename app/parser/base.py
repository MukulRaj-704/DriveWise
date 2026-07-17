"""PDF parser abstraction. Swap engines (PyMuPDF, pdfplumber, ...) without touching callers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParsedBlock:
    """A single unit of extracted content (paragraph, heading, or table)."""

    text: str
    page_number: int
    block_type: str = "paragraph"  # paragraph | heading | table
    heading_path: list[str] = field(default_factory=list)  # document hierarchy, e.g. ["Safety", "Airbags"]


@dataclass
class ParsedDocument:
    blocks: list[ParsedBlock]
    page_count: int
    title: str | None = None


class BasePDFParser(ABC):
    """Interface every PDF parsing engine must implement."""

    @abstractmethod
    def parse(self, file_path: str) -> ParsedDocument:
        """Parse a PDF at `file_path` into structured blocks with page numbers and hierarchy."""
        raise NotImplementedError
