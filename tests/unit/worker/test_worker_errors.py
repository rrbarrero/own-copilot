from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.ingestion.domain.document import (
    Document,
    DocumentStatus,
    DocumentType,
    SourceType,
)
from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.infra.in_memory_document_repo import InMemoryDocumentRepo
from app.ingestion.infra.in_memory_job_repo import InMemoryJobRepo
from app.worker.application.document_processing_service import (
    DocumentProcessingService,
)
from app.worker.application.ingestion_worker import IngestionWorker
from app.worker.application.job_handlers.process_document_handler import (
    ProcessDocumentJobHandler,
)
from app.worker.application.pipeline import Pipeline
from app.worker.domain.pipeline_context import PipelineContext


class FailingPipeline(Pipeline):
    def __init__(self, error_message: str):
        super().__init__(steps=[])
        self.error_message = error_message

    async def run(self, ctx: PipelineContext) -> None:  # noqa: ARG002
        raise Exception(self.error_message)


class SuccessPipeline(Pipeline):
    def __init__(self):
        super().__init__(steps=[])

    async def run(self, ctx: PipelineContext) -> None:  # noqa: ARG002
        pass


@pytest.mark.asyncio
async def test_worker_persists_last_error_on_failure():
    # 1. Setup
    job_repo = InMemoryJobRepo()
    doc_repo = InMemoryDocumentRepo()
    error_msg = "Critical error during pipeline execution"
    pipeline = FailingPipeline(error_msg)

    # Use a real handler with the failing pipeline
    processing_service = DocumentProcessingService(doc_repo=doc_repo, pipeline=pipeline)
    handler = ProcessDocumentJobHandler(processing_service)

    worker = IngestionWorker(job_repo=job_repo, handlers={"test": handler})

    doc_id = uuid4()
    doc = Document(
        uuid=doc_id,
        source_type=SourceType.UPLOAD,
        source_id="usr-123",
        path="foo.txt",
        filename="foo.txt",
        extension="txt",
        doc_type=DocumentType.TEXT,
        processing_status=DocumentStatus.QUEUED,
        size_bytes=10,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(doc)

    job_id = uuid4()
    job = Job(
        id=job_id,
        queue_name="ingestion",
        job_type="test",
        payload={"doc_uuid": str(doc_id)},
        status=JobStatus.PENDING,
        attempts=0,
        max_attempts=3,
        run_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await job_repo.save(job)

    # 2. Execute process_job
    await worker._process_job(job)

    # 3. Assertions on job
    assert job.status == JobStatus.FAILED
    assert job.last_error == error_msg

    # 4. Assertions on document
    saved_doc = await doc_repo.get_by_uuid(str(doc_id))
    assert saved_doc is not None
    assert saved_doc.processing_status == DocumentStatus.ERROR
    assert saved_doc.last_error == error_msg


@pytest.mark.asyncio
async def test_worker_updates_document_status_on_success():
    # 1. Setup
    job_repo = InMemoryJobRepo()
    doc_repo = InMemoryDocumentRepo()
    pipeline = SuccessPipeline()

    processing_service = DocumentProcessingService(doc_repo=doc_repo, pipeline=pipeline)
    handler = ProcessDocumentJobHandler(processing_service)

    worker = IngestionWorker(job_repo=job_repo, handlers={"test": handler})

    doc_id = uuid4()
    doc = Document(
        uuid=doc_id,
        source_type=SourceType.UPLOAD,
        source_id="usr-123",
        path="foo.txt",
        filename="foo.txt",
        extension="txt",
        doc_type=DocumentType.TEXT,
        processing_status=DocumentStatus.QUEUED,
        size_bytes=10,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(doc)

    job_id = uuid4()
    job = Job(
        id=job_id,
        queue_name="ingestion",
        job_type="test",
        payload={"doc_uuid": str(doc_id)},
        status=JobStatus.PENDING,
        attempts=0,
        max_attempts=3,
        run_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await job_repo.save(job)

    # 2. Execute process_job
    await worker._process_job(job)

    # 3. Assertions
    assert job.status == JobStatus.COMPLETED

    saved_doc = await doc_repo.get_by_uuid(str(doc_id))
    assert saved_doc is not None
    assert saved_doc.processing_status == DocumentStatus.READY
    assert saved_doc.indexed_at is not None
