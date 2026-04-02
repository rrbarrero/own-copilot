from app.worker.domain.chunker_proto import ChunkerProto
from app.worker.domain.document_chunking_context import DocumentChunkingContext
from app.worker.infrastructure.chunkers.chunking_strategy_selector import (
    ChunkingStrategySelector,
)


class DocumentAwareChunker(ChunkerProto):
    def __init__(self, selector: ChunkingStrategySelector):
        self.selector = selector

    def chunk(
        self, text: str, context: DocumentChunkingContext | None = None
    ) -> list[str]:
        if not context:
            context = DocumentChunkingContext()
        strategy = self.selector.select(context)
        return strategy.chunk(text)
