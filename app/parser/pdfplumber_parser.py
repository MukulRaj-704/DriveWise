"""Alternate PDF parser built on pdfplumber. Better table extraction, slower than PyMuPDF.

Selected via PDF_PARSER=pdfplumber in the environment.
"""
from __future__ import annotations

from app.core.exceptions import ParsingError
from app.parser.base import BasePDFParser, ParsedBlock, ParsedDocument


class PDFPlumberParser(BasePDFParser):
    def parse(self, file_path: str) -> ParsedDocument:
        try:
            import pdfplumber
        except ImportError as exc:  # pragma: no cover
            raise ParsingError("pdfplumber is not installed.") from exc

        blocks: list[ParsedBlock] = []
        try:
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page_index, page in enumerate(pdf.pages):
                    page_number = page_index + 1

                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        line = line.strip()
                        if line:
                            blocks.append(ParsedBlock(text=line, page_number=page_number))

                    for table in page.extract_tables() or []:
                        rendered = "\n".join(
                            " | ".join(cell or "" for cell in row) for row in table if row
                        )
                        if rendered.strip():
                            blocks.append(
                                ParsedBlock(text=rendered, page_number=page_number, block_type="table")
                            )
        except Exception as exc:
            raise ParsingError(f"Could not parse PDF with pdfplumber: {exc}") from exc

        return ParsedDocument(blocks=blocks, page_count=page_count)
