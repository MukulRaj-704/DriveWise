"""Upload validation / sanitization helpers."""
from __future__ import annotations

from app.core.exceptions import FileTooLargeError, InvalidFileError

_PDF_MAGIC = b"%PDF-"


def validate_pdf_upload(filename: str, file_bytes: bytes, max_size_mb: int) -> None:
    if not filename.lower().endswith(".pdf"):
        raise InvalidFileError("Only .pdf files are accepted.")

    if not file_bytes.startswith(_PDF_MAGIC):
        raise InvalidFileError("File does not appear to be a valid PDF.")

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise FileTooLargeError(f"File exceeds the maximum size of {max_size_mb}MB.")
