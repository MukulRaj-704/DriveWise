from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import User
from app.schemas.schemas import BrochureListResponse, BrochureOut
from app.services.brochure_service import BrochureService
from app.utils.storage import get_storage_provider

router = APIRouter(prefix="/brochure", tags=["Brochure"])


def _service(db: AsyncSession, settings: Settings) -> BrochureService:
    return BrochureService(db, get_storage_provider(settings), settings)


@router.post("/upload", response_model=BrochureOut, status_code=201)
async def upload_brochure(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> BrochureOut:
    file_bytes = await file.read()
    return await _service(db, settings).upload(user.id, file.filename, file_bytes)


@router.get("", response_model=BrochureListResponse)
async def list_brochures(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> BrochureListResponse:
    brochures = await _service(db, settings).list_for_user(user.id)
    return BrochureListResponse(brochures=brochures, total=len(brochures))


@router.delete("/{brochure_id}", status_code=204, response_model=None)
async def delete_brochure(
    brochure_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> None:
    await _service(db, settings).delete(user.id, brochure_id)