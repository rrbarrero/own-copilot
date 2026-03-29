import logging
from datetime import UTC, datetime
from uuid import UUID

from app.ingestion.domain.document import DocumentStatus
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.worker.application.pipeline import Pipeline
from app.worker.domain.pipeline_context import PipelineContext

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    def __init__(self, doc_repo: DocumentRepoProto, pipeline: Pipeline):
        self._doc_repo = doc_repo
        self._pipeline = pipeline

    async def process(
        self, document_uuid: str | UUID, correlation_id: str | UUID | None = None
    ) -> None:
        """
        Executes the full pipeline for a single document.
        Manages its lifecycle status (ingesting, ready, error).
        """
        doc_uuid_str = str(document_uuid)
        doc = await self._doc_repo.get_by_uuid(doc_uuid_str)

        if not doc:
            raise ValueError(f"Document with UUID {doc_uuid_str} not found.")

        # 1. Update status to INGESTING
        doc.processing_status = DocumentStatus.INGESTING
        doc.updated_at = datetime.now(UTC)
        await self._doc_repo.save(doc)

        # 2. Initialize context
        ctx = PipelineContext(
            document_id=doc_uuid_str,
            job_id=str(correlation_id) if correlation_id else doc_uuid_str,
            job_type="process_document",
            payload={"doc_uuid": doc_uuid_str},
            repository_sync_id=str(correlation_id) if correlation_id else None,
        )

        try:
            # 3. Run pipeline
            await self._pipeline.run(ctx)

            # 4. Mark as READY
            doc.processing_status = DocumentStatus.READY
            doc.indexed_at = datetime.now(UTC)
            doc.updated_at = datetime.now(UTC)
            await self._doc_repo.save(doc)

        except Exception as e:
            logger.error(f"Failed to process document {doc_uuid_str}: {e}")
            doc.processing_status = DocumentStatus.ERROR
            doc.last_error = str(e)
            doc.updated_at = datetime.now(UTC)
            await self._doc_repo.save(doc)
            raise e
