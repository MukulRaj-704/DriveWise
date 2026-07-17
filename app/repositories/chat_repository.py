from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import ChatMessage, ChatSession


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: str, title: str = "New conversation") -> ChatSession:
        session = ChatSession(user_id=user_id, title=title)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: str, user_id: str) -> ChatSession | None:
        result = await self.db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, user_id: str) -> list[ChatSession]:
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_message(
        self, session_id: str, role: str, content: str, sources: list[dict] | None = None
    ) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content, sources=sources)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def delete_session(self, session: ChatSession) -> None:
        await self.db.delete(session)
        await self.db.commit()

    async def get_recent_history_text(self, session_id: str, max_messages: int = 6) -> str | None:
        result = await self.db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.desc()).limit(max_messages)
        )
        messages = list(reversed(result.scalars().all()))
        if not messages:
            return None
        return "\n".join(f"{m.role}: {m.content}" for m in messages)
