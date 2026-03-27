from dataclasses import dataclass
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


@dataclass
class Document:
    uuid: UUID
    content: str
    source_type: SourceType
    source_id: str
    path: str
    filename: str
    extension: str
    doc_type: DocumentType
    language: str | None = None
    repository_url: str | None = None
    branch: str | None = None
