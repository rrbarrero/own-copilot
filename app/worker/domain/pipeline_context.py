from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
