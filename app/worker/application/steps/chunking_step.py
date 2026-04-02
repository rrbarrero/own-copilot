from app.worker.domain.chunker_proto import ChunkerProto
from app.worker.domain.document_chunking_context import DocumentChunkingContext
from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.step_proto import StepProto


class ChunkingStep(StepProto):
    def __init__(self, chunker: ChunkerProto):
        self.chunker = chunker

    async def run(self, ctx: PipelineContext):
        # 1. Check if original_bytes are present (loaded by previous step)
        if ctx.original_bytes is None:
            raise ValueError(
                "original_bytes are missing in context. Run LoadDocumentStep first."
            )

        # 2. Handle empty files gracefully
        if not ctx.original_bytes:
            ctx.chunks = []
            return

        normalized_format = None
        if ctx.normalized_document:
            text = str(ctx.normalized_document.get("text", ""))
            normalized_format = ctx.normalized_document.get("format")
        else:
            # 3. Decode bytes to text (assuming UTF-8 for now)
            try:
                text = ctx.original_bytes.decode("utf-8")
            except UnicodeDecodeError as e:
                raise ValueError("Failed to decode document content as UTF-8.") from e

        # 3. Create chunks using the domain chunker with document metadata
        doc_context = DocumentChunkingContext(
            filename=ctx.filename,
            extension=ctx.extension,
            doc_type=ctx.doc_type,
            language=ctx.language,
            mime_type=ctx.mime_type,
            normalized_format=normalized_format,
        )
        chunk_contents = self.chunker.chunk(text, context=doc_context)

        # 4. Map to context chunk structure
        ctx.chunks = [
            {"content": content, "chunk_index": idx}
            for idx, content in enumerate(chunk_contents)
        ]
