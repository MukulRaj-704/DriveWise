from __future__ import annotations

from fastapi import APIRouter

from app.config.settings import get_settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "llm_provider": settings.LLM_PROVIDER,
        "vector_db": settings.VECTOR_DB,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
    }
