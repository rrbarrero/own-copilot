from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class SourceType(Enum):
    UPLOAD = "upload"
    REPOSITORY = "repository"


class DocumentType(Enum):
    MARKDOWN = "markdown"
    TEXT = "text"
    CODE = "code"
    CONFIG = "config"


class DocumentStatus(Enum):
    QUEUED = "queued"
    INGESTING = "ingesting"
    READY = "ready"
    ERROR = "error"


@dataclass
class Document:
    uuid: UUID

    source_type: SourceType
    source_id: str
    path: str
    filename: str
    extension: str
    doc_type: DocumentType
    processing_status: DocumentStatus
    size_bytes: int
    created_at: datetime
    updated_at: datetime
    language: str | None = None
    upload_batch_id: UUID | None = None
    repository_sync_id: UUID | None = None
    repository_id: UUID | None = None
    repository_url: str | None = None
    content_hash: str | None = None
    branch: str | None = None
    mime_type: str | None = None
    indexed_at: datetime | None = None
    last_error: str | None = None
    version: int = 1
    superseded_by: UUID | None = None
