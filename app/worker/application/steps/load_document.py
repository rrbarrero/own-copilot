from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.domain.storage_repo_proto import StorageRepoProto
from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.step_proto import StepProto


class LoadDocumentStep(StepProto):
    def __init__(
        self,
        document_repo: DocumentRepoProto,
        storage_repo: StorageRepoProto,
    ):
        self.document_repo = document_repo
        self.storage_repo = storage_repo

    async def run(self, ctx: PipelineContext):
        # 1. Get document_id from payload
        doc_id = ctx.payload.get("document_id")
        if not doc_id:
            raise ValueError("document_id is required in context payload")

        # 2. Get document metadata from repository
        doc = await self.document_repo.get_by_uuid(doc_id)
        if not doc:
            raise ValueError(f"Document with uuid {doc_id} not found")

        # 3. Download document content using repository path
        # The current storage protocol is synchronous
        content = self.storage_repo.get(doc.path)
        if content is None:
            raise ValueError(
                f"Content for document {doc_id} at path {doc.path} not found"
            )

        # 4. Update pipeline context
        ctx.document_id = str(doc.uuid)
        ctx.original_bytes = content
        ctx.repository_sync_id = (
            str(doc.repository_sync_id) if doc.repository_sync_id else None
        )
