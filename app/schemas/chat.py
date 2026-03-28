from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ScopeType(StrEnum):
    REPOSITORY = "repository"
    DOCUMENT = "document"


class ChatScope(BaseModel):
    type: ScopeType
    repository_id: UUID | None = None
    document_id: UUID | None = None


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, description="La pregunta del usuario")
    scope: ChatScope = Field(..., description="El ámbito de la búsqueda")


class ChatCitation(BaseModel):
    document_id: UUID
    path: str
    filename: str
    chunk_index: int


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation] = Field(default_factory=list)
