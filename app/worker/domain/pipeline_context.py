from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ingestion.domain.document import SourceType


class PipelineContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    job_id: str
    job_type: str
    payload: dict[str, Any]

    document_id: str | None = None
    repository_sync_id: str | None = None

    filename: str | None = None
    extension: str | None = None
    doc_type: str | None = None
    language: str | None = None
    mime_type: str | None = None
    source_path: str | None = None
    source_type: str | None = None

    original_bytes: bytes | None = None
    normalized_document: dict[str, Any] | None = None
    chunks: list[dict[str, Any]] = Field(default_factory=list)
    embeddings: list[list[float]] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("job_id", "job_type")
    @classmethod
    def not_empty(cls, v: str):
        if not v.strip():
            raise ValueError("Field must not be empty.")
        return v

    @field_validator("source_type")
    @classmethod
    def valid_source_type(cls, v: str | None):
        if v is None:
            return v
        allowed = {source_type.value for source_type in SourceType}
        if v not in allowed:
            raise ValueError("Invalid source_type.")
        return v
