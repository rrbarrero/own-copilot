from typing import Any, Protocol

from app.worker.domain.document_chunking_context import DocumentChunkingContext


class DocumentNormalizerProto(Protocol):
    def supports(self, context: DocumentChunkingContext) -> bool: ...

    def normalize(
        self, content: bytes, context: DocumentChunkingContext
    ) -> dict[str, Any]: ...
