from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Brochure, Chunk


class BrochureRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **fields) -> Brochure:
        brochure = Brochure(**fields)
        self.db.add(brochure)
        await self.db.commit()
        await self.db.refresh(brochure)
        return brochure

    async def get_by_id(self, brochure_id: str, owner_id: str) -> Brochure | None:
        result = await self.db.execute(
            select(Brochure).where(Brochure.id == brochure_id, Brochure.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, owner_id: str) -> list[Brochure]:
        result = await self.db.execute(
            select(Brochure).where(Brochure.owner_id == owner_id).order_by(Brochure.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(self, brochure: Brochure, *, status: str, error_message: str | None = None, **fields) -> Brochure:
        brochure.status = status
        brochure.error_message = error_message
        for k, v in fields.items():
            setattr(brochure, k, v)
        await self.db.commit()
        await self.db.refresh(brochure)
        return brochure

    async def delete(self, brochure: Brochure) -> None:
        await self.db.delete(brochure)
        await self.db.commit()


class ChunkRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_create(self, chunks: list[Chunk]) -> None:
        self.db.add_all(chunks)
        await self.db.commit()

    async def list_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        if not chunk_ids:
            return []
        result = await self.db.execute(select(Chunk).where(Chunk.id.in_(chunk_ids)))
        return list(result.scalars().all())

    async def list_by_brochure(self, brochure_id: str) -> list[Chunk]:
        result = await self.db.execute(select(Chunk).where(Chunk.brochure_id == brochure_id))
        return list(result.scalars().all())

    async def list_by_brochures(self, brochure_ids: list[str]) -> list[Chunk]:
        if not brochure_ids:
            return []
        result = await self.db.execute(select(Chunk).where(Chunk.brochure_id.in_(brochure_ids)))
        return list(result.scalars().all())

    async def delete_by_brochure(self, brochure_id: str) -> None:
        await self.db.execute(delete(Chunk).where(Chunk.brochure_id == brochure_id))
        await self.db.commit()
