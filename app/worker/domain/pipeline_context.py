from dataclasses import dataclass, field


@dataclass
class PipelineContext:
    job_id: str
    job_type: str
    payload: dict

    document_id: str | None = None
    repository_sync_id: str | None = None

    original_bytes: bytes | None = None
    normalized_document: dict | None = None
    chunks: list[dict] = field(default_factory=list)
    embeddings: list[list[float]] = field(default_factory=list)

    metadata: dict = field(default_factory=dict)
