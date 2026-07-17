"""Default PDF parser, built on PyMuPDF (fitz).

Responsibilities:
 - extract text per page, preserving reading order
 - detect probable headings via font size relative to the page's body-text size
 - drop repeated headers/footers (lines that appear on >60% of pages at the
   same vertical position)
 - build a lightweight heading hierarchy so chunks can carry a `section` path
"""
from __future__ import annotations

from collections import Counter

from app.core.exceptions import ParsingError
from app.parser.base import BasePDFParser, ParsedBlock, ParsedDocument


class PyMuPDFParser(BasePDFParser):
    HEADING_SIZE_RATIO = 1.15  # font size must be >=15% larger than body text to count as heading

    def parse(self, file_path: str) -> ParsedDocument:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:  # pragma: no cover
            raise ParsingError("PyMuPDF is not installed.") from exc

        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            raise ParsingError(f"Could not open PDF: {exc}") from exc

        try:
            page_lines: list[list[dict]] = []
            for page in doc:
                page_lines.append(self._extract_lines(page))

            repeated = self._find_repeated_lines(page_lines)
            body_size = self._estimate_body_font_size(page_lines)

            blocks: list[ParsedBlock] = []
            heading_stack: list[str] = []

            for page_index, lines in enumerate(page_lines):
                page_number = page_index + 1
                for line in lines:
                    text = line["text"].strip()
                    if not text or text in repeated:
                        continue

                    is_heading = line["size"] >= body_size * self.HEADING_SIZE_RATIO and len(text) < 120
                    if is_heading:
                        heading_stack = [text]  # single-level hierarchy is enough for brochures
                        blocks.append(
                            ParsedBlock(
                                text=text,
                                page_number=page_number,
                                block_type="heading",
                                heading_path=list(heading_stack),
                            )
                        )
                    else:
                        blocks.append(
                            ParsedBlock(
                                text=text,
                                page_number=page_number,
                                block_type="paragraph",
                                heading_path=list(heading_stack),
                            )
                        )

            title = doc.metadata.get("title") or None
            page_count = doc.page_count
            return ParsedDocument(blocks=blocks, page_count=page_count, title=title)
        finally:
            doc.close()

    @staticmethod
    def _extract_lines(page) -> list[dict]:
        """Return a flat list of {text, size, y} for each line on the page."""
        lines_out: list[dict] = []
        try:
            page_dict = page.get_text("dict")
        except Exception:
            return lines_out

        for block in page_dict.get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s.get("text", "") for s in spans).strip()
                if not text:
                    continue
                size = max((s.get("size", 0) for s in spans), default=0)
                y = line.get("bbox", [0, 0, 0, 0])[1]
                lines_out.append({"text": text, "size": size, "y": y})
        return lines_out

    @staticmethod
    def _find_repeated_lines(page_lines: list[list[dict]]) -> set[str]:
        """Lines (e.g. running headers/footers) that show up on most pages are noise."""
        if len(page_lines) < 3:
            return set()
        counts: Counter[str] = Counter()
        for lines in page_lines:
            seen_this_page = {l["text"] for l in lines}
            counts.update(seen_this_page)
        threshold = max(3, int(len(page_lines) * 0.6))
        return {text for text, c in counts.items() if c >= threshold}

    @staticmethod
    def _estimate_body_font_size(page_lines: list[list[dict]]) -> float:
        sizes = [round(l["size"], 1) for lines in page_lines for l in lines if l["size"]]
        if not sizes:
            return 10.0
        return Counter(sizes).most_common(1)[0][0]
