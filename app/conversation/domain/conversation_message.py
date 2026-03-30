from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID


@dataclass(frozen=True)
class ConversationMessage:
    id: UUID
    conversation_id: UUID
    role: str  # "user" | "assistant"
    content: str
    rewritten_question: str | None = None
    citations_json: list[dict] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
