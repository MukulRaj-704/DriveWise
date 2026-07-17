from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.models import User
from app.schemas.schemas import ChatHistoryResponse, ChatRequest, ChatResponse, ChatSessionDetail
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    return await ChatService(db).ask(user.id, payload)


@router.get("/history", response_model=ChatHistoryResponse)
async def chat_history(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatHistoryResponse:
    sessions = await ChatService(db).get_history(user.id)
    return ChatHistoryResponse(sessions=sessions)


@router.get("/{session_id}", response_model=ChatSessionDetail)
async def chat_session_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChatSessionDetail:
    return await ChatService(db).get_session_detail(user.id, session_id)


@router.delete("/{session_id}", status_code=204, response_model=None)
async def delete_chat(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await ChatService(db).delete_session(user.id, session_id)