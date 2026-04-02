from typing import Protocol

from app.worker.domain.document_chunking_context import DocumentChunkingContext


class ChunkerProto(Protocol):
    def chunk(
        self, text: str, context: DocumentChunkingContext | None = None
    ) -> list[str]: ...
