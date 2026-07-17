from __future__ import annotations

from fastapi import APIRouter

from app.api.auth_routes import router as auth_router
from app.api.brochure_routes import router as brochure_router
from app.api.chat_routes import router as chat_router
from app.api.health_routes import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(brochure_router)
api_router.include_router(chat_router)
