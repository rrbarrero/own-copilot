from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Conversation:
    id: UUID
    scope_type: str  # "repository" | "document"
    repository_id: UUID | None
    document_id: UUID | None
    created_at: datetime
    updated_at: datetime
