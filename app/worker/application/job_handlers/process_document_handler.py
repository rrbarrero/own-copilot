import logging

from app.ingestion.domain.job import Job
from app.worker.application.document_processing_service import (
    DocumentProcessingService,
)
from app.worker.application.job_handler_proto import JobHandlerProto

logger = logging.getLogger(__name__)


class ProcessDocumentJobHandler(JobHandlerProto):
    """
    Handler for existing single document upload ingestion jobs.
    """

    def __init__(self, processing_service: DocumentProcessingService):
        self._processing_service = processing_service

    async def handle(self, job: Job) -> None:
        document_id = job.payload.get("doc_uuid")
        if not document_id:
            raise ValueError(f"Job {job.id} does not contain 'doc_uuid' in payload.")

        logger.info(
            f"Handling process_document for job {job.id}, document {document_id}"
        )
        await self._processing_service.process(document_id, correlation_id=job.id)
