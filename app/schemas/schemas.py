"""Pydantic v2 schemas for API I/O."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth / Users ----------

class UserRegister(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: EmailStr
    full_name: str
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ---------- Brochure ----------

class BrochureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    file_name: str
    car_name: str | None = None
    manufacturer: str | None = None
    year: str | None = None
    page_count: int
    status: str
    created_at: datetime


class BrochureListResponse(BaseModel):
    brochures: list[BrochureOut]
    total: int


# ---------- Chat ----------

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    brochure_ids: list[str] | None = Field(
        default=None, description="Restrict retrieval to these brochures; None = all of the user's brochures."
    )
    filters: dict[str, str] | None = Field(
        default=None, description="Metadata filters, e.g. {'car_name': 'Creta', 'fuel_type': 'Petrol'}"
    )


class SourceAttribution(BaseModel):
    chunk_id: str
    brochure_id: str
    brochure_name: str
    page: int | None = None
    section: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceAttribution]


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    role: str
    content: str
    sources: list[dict] | None = None
    created_at: datetime


class ChatSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    created_at: datetime


class ChatSessionDetail(ChatSessionOut):
    messages: list[ChatMessageOut]


class ChatHistoryResponse(BaseModel):
    sessions: list[ChatSessionOut]


# ---------- Generic ----------

class ErrorResponse(BaseModel):
    detail: str
    error_type: str | None = None
