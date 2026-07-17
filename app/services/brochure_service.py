"""Brochure ingestion service: upload -> parse -> chunk -> embed -> index.

This is the write-side counterpart to the RAG pipeline's read-side. It owns
turning a raw PDF into searchable, metadata-rich chunks.
"""
from __future__ import annotations

import os
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.chunking.chunker import SemanticChunker
from app.config.settings import Settings
from app.core.exceptions import BrochureNotFoundError, ParsingError
from app.dependencies.providers import (
    get_embedding_provider_singleton,
    get_pdf_parser_singleton,
    get_vector_store_singleton,
)
from app.logging.logger import get_logger, log_event
from app.models.models import Brochure, Chunk
from app.parser.base import ParsedDocument
from app.repositories.brochure_repository import BrochureRepository, ChunkRepository
from app.schemas.schemas import BrochureOut
from app.utils.storage import BaseStorageProvider
from app.utils.validation import validate_pdf_upload
from app.vectorstore.base import VectorRecord

logger = get_logger(__name__)


def _guess_car_metadata(filename: str) -> dict[str, str | None]:
    """Best-effort metadata guess from the filename (e.g. 'Hyundai_Creta_2024_Brochure.pdf').
    This is intentionally simple; a production system might use an LLM extraction pass
    over page 1, but that's an easy additive step behind the same interface."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    tokens = re.split(r"[_\-\s]+", stem)
    year_match = next((t for t in tokens if re.fullmatch(r"(19|20)\d{2}", t)), None)
    words = [t for t in tokens if t.lower() not in {"brochure", "catalogue", "catalog", "spec", "specs"} and t != year_match]
    car_name = " ".join(words[:3]) if words else stem
    manufacturer = words[0] if words else None
    return {"car_name": car_name or None, "manufacturer": manufacturer, "year": year_match}


class BrochureService:
    def __init__(self, db: AsyncSession, storage: BaseStorageProvider, settings: Settings):
        self.db = db
        self.storage = storage
        self.settings = settings
        self.brochure_repo = BrochureRepository(db)
        self.chunk_repo = ChunkRepository(db)

    async def upload(self, owner_id: str, filename: str, file_bytes: bytes) -> BrochureOut:
        validate_pdf_upload(filename, file_bytes, self.settings.MAX_UPLOAD_SIZE_MB)

        storage_path = await self.storage.save(file_bytes, filename)
        guess = _guess_car_metadata(filename)

        brochure = await self.brochure_repo.create(
            owner_id=owner_id,
            file_name=filename,
            storage_path=storage_path,
            car_name=guess["car_name"],
            manufacturer=guess["manufacturer"],
            year=guess["year"],
            status="processing",
        )

        try:
            await self._index_brochure(brochure)
        except Exception as exc:
            log_event(logger, 40, "brochure_indexing_failed", brochure_id=brochure.id, error=str(exc))
            await self.brochure_repo.update_status(brochure, status="failed", error_message=str(exc))
            raise ParsingError(f"Failed to index brochure: {exc}") from exc

        return BrochureOut.model_validate(brochure)

    async def _index_brochure(self, brochure: Brochure) -> None:
        parser = get_pdf_parser_singleton()
        embedder = get_embedding_provider_singleton()
        vector_store = get_vector_store_singleton()

        file_path = self.storage.resolve_path(brochure.storage_path)
        parsed: ParsedDocument = parser.parse(file_path)

        chunker = SemanticChunker(
            max_tokens=self.settings.CHUNK_MAX_TOKENS, overlap_tokens=self.settings.CHUNK_OVERLAP_TOKENS
        )
        semantic_chunks = chunker.chunk(parsed.blocks)

        if not semantic_chunks:
            raise ParsingError("No extractable text found in this PDF.")

        db_chunks = [
            Chunk(
                id=sc.chunk_id,
                brochure_id=brochure.id,
                text=sc.text,
                car_name=brochure.car_name,
                manufacturer=brochure.manufacturer,
                variant=None,
                page_number=sc.page_number,
                section=sc.section,
                year=brochure.year,
                fuel_type=None,
                transmission=None,
                chunk_index=sc.chunk_index,
            )
            for sc in semantic_chunks
        ]

        embeddings = embedder.embed_documents([c.text for c in semantic_chunks])

        records = [
            VectorRecord(
                id=sc.chunk_id,
                vector=vector,
                metadata={
                    "brochure_id": brochure.id,
                    "car_name": brochure.car_name,
                    "manufacturer": brochure.manufacturer,
                    "page_number": sc.page_number,
                    "section": sc.section,
                    "year": brochure.year,
                },
            )
            for sc, vector in zip(semantic_chunks, embeddings)
        ]

        await self.chunk_repo.bulk_create(db_chunks)
        vector_store.add(records)

        await self.brochure_repo.update_status(
            brochure, status="ready", page_count=parsed.page_count
        )
        log_event(logger, 20, "brochure_indexed", brochure_id=brochure.id, chunks=len(db_chunks), pages=parsed.page_count)

    async def list_for_user(self, owner_id: str) -> list[BrochureOut]:
        brochures = await self.brochure_repo.list_for_user(owner_id)
        return [BrochureOut.model_validate(b) for b in brochures]

    async def delete(self, owner_id: str, brochure_id: str) -> None:
        brochure = await self.brochure_repo.get_by_id(brochure_id, owner_id)
        if brochure is None:
            raise BrochureNotFoundError()

        vector_store = get_vector_store_singleton()
        chunks = await self.chunk_repo.list_by_brochure(brochure_id)
        vector_store.delete([c.id for c in chunks])

        await self.storage.delete(brochure.storage_path)
        await self.brochure_repo.delete(brochure)
        log_event(logger, 20, "brochure_deleted", brochure_id=brochure_id)
