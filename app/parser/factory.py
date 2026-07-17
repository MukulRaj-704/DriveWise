from app.config.settings import Settings
from app.parser.base import BasePDFParser
from app.parser.pdfplumber_parser import PDFPlumberParser
from app.parser.pymupdf_parser import PyMuPDFParser


def get_pdf_parser(settings: Settings) -> BasePDFParser:
    if settings.PDF_PARSER == "pdfplumber":
        return PDFPlumberParser()
    return PyMuPDFParser()
