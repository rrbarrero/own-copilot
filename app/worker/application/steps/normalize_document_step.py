from app.worker.domain.document_chunking_context import DocumentChunkingContext
from app.worker.domain.document_normalizer_proto import DocumentNormalizerProto
from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.step_proto import StepProto


class NormalizeDocumentStep(StepProto):
    def __init__(self, normalizers: list[DocumentNormalizerProto]):
        self.normalizers = normalizers

    async def run(self, ctx: PipelineContext):
        if ctx.original_bytes is None:
            raise ValueError(
                "original_bytes are missing in context. Run LoadDocumentStep first."
            )

        if not ctx.original_bytes:
            ctx.normalized_document = None
            return

        doc_context = DocumentChunkingContext(
            filename=ctx.filename,
            extension=ctx.extension,
            doc_type=ctx.doc_type,
            language=ctx.language,
            mime_type=ctx.mime_type,
        )

        for normalizer in self.normalizers:
            if normalizer.supports(doc_context):
                ctx.normalized_document = normalizer.normalize(
                    ctx.original_bytes, doc_context
                )
                return

        ctx.normalized_document = None
