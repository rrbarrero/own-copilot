from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.step_proto import StepProto


class SaveChunksStep(StepProto):
    def __init__(self, document_repo: DocumentRepoProto):
        self.document_repo = document_repo

    async def run(self, ctx: PipelineContext):
        # 1. Check if we have a document_uuid and chunks
        if not ctx.document_id:
            raise ValueError("document_id is missing in context.")

        if not ctx.chunks:
            # We could log a warning but maybe there's nothing to save
            return

        # 2. Persist chunks in the repository
        await self.document_repo.save_chunks(
            document_uuid=ctx.document_id, chunks=ctx.chunks
        )
