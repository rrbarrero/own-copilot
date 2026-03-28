from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class RetrievedChunk:
    document_uuid: UUID
    chunk_index: int
    content: str
    path: str
    filename: str
    source_type: str
    repository_id: UUID | None
    score: float
    metadata: dict[str, Any]
