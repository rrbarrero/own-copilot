from dataclasses import dataclass


@dataclass
class DocumentChunkingContext:
    filename: str | None = None
    extension: str | None = None
    doc_type: str | None = None
    language: str | None = None
