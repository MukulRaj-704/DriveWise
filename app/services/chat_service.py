"""Chat service: ties together chat history persistence and the RAG pipeline."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ChatNotFoundError
from app.dependencies.providers import get_llm_provider_dependency, get_retriever
from app.llm.base import BaseLLMProvider
from app.logging.logger import get_logger, log_event
from app.rag.pipeline import RagPipeline
from app.rag.retriever import Retriever
from app.repositories.brochure_repository import BrochureRepository, ChunkRepository
from app.repositories.chat_repository import ChatRepository
from app.schemas.schemas import ChatRequest, ChatResponse, ChatSessionDetail

logger = get_logger(__name__)


class ChatService:
    def __init__(
        self,
        db: AsyncSession,
        retriever: Retriever | None = None,
        llm: BaseLLMProvider | None = None,
    ):
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.brochure_repo = BrochureRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.retriever = retriever or get_retriever()
        self.llm = llm or get_llm_provider_dependency()
        print("LLM INSTANCE:", type(self.llm)) 
        self.pipeline = RagPipeline(self.retriever, self.llm)

    async def ask(self, user_id: str, request: ChatRequest) -> ChatResponse:
        session = None
        if request.session_id:
            session = await self.chat_repo.get_session(request.session_id, user_id)
            if session is None:
                raise ChatNotFoundError()
        else:
            title = request.message[:60]
            session = await self.chat_repo.create_session(user_id, title=title)

        brochures = await self.brochure_repo.list_for_user(user_id)
        ready_brochures = [b for b in brochures if b.status == "ready"]

        if request.brochure_ids:
            ready_brochures = [b for b in ready_brochures if b.id in request.brochure_ids]

        brochure_names = {b.id: b.car_name or b.file_name for b in ready_brochures}

        chunks = await self.chunk_repo.list_by_brochures([b.id for b in ready_brochures])
        chunk_texts = {c.id: c.text for c in chunks}

        filters = dict(request.filters or {})
        if request.brochure_ids and len(request.brochure_ids) == 1:
            filters.setdefault("brochure_id", request.brochure_ids[0])

        history = await self.chat_repo.get_recent_history_text(session.id)

        await self.chat_repo.add_message(session.id, role="user", content=request.message)

        result = await self.pipeline.answer(
            question=request.message,
            chunk_texts=chunk_texts,
            brochure_names=brochure_names,
            filters=filters or None,
            history=history,
        )

        await self.chat_repo.add_message(
            session.id,
            role="assistant",
            content=result.answer,
            sources=[s.model_dump() for s in result.sources],
        )

        log_event(logger, 20, "chat_answered", session_id=session.id, sources=len(result.sources))

        return ChatResponse(session_id=session.id, answer=result.answer, sources=result.sources)

    async def get_history(self, user_id: str):
        return await self.chat_repo.list_sessions(user_id)

    async def get_session_detail(self, user_id: str, session_id: str) -> ChatSessionDetail:
        session = await self.chat_repo.get_session(session_id, user_id)
        if session is None:
            raise ChatNotFoundError()
        return ChatSessionDetail.model_validate(session)

    async def delete_session(self, user_id: str, session_id: str) -> None:
        session = await self.chat_repo.get_session(session_id, user_id)
        if session is None:
            raise ChatNotFoundError()
        await self.chat_repo.delete_session(session)
