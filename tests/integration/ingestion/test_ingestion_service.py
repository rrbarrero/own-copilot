import uuid

import pytest

from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.domain.document import DocumentStatus, SourceType
from app.ingestion.domain.job import JobStatus
from app.ingestion.infra.in_memory_document_repo import InMemoryDocumentRepo
from app.ingestion.infra.in_memory_job_repo import InMemoryJobRepo
from app.ingestion.infra.in_memory_storage_repo import InMemoryStorageRepo


@pytest.fixture
def doc_repo():
    return InMemoryDocumentRepo()


@pytest.fixture
def storage_repo():
    return InMemoryStorageRepo()


@pytest.fixture
def job_repo():
    return InMemoryJobRepo()


@pytest.fixture
def ingestion_service(doc_repo, storage_repo, job_repo):
    return IngestionService(
        doc_repo=doc_repo, storage_repo=storage_repo, job_repo=job_repo
    )


@pytest.mark.asyncio
async def test_upload_file_success(ingestion_service, doc_repo, storage_repo, job_repo):
    # Given
    filename = "test_document.txt"
    content = b"Hello world, this is a test document content."
    mime_type = "text/plain"
    batch_id = uuid.uuid4()

    # When
    doc_uuid = await ingestion_service.upload_file(
        filename=filename,
        content_bytes=content,
        mime_type=mime_type,
        batch_id=batch_id,
    )

    # Then
    # 1. Document persisted
    doc = await doc_repo.get_by_uuid(str(doc_uuid))
    assert doc is not None
    assert doc.filename == filename
    assert doc.source_type == SourceType.UPLOAD
    assert doc.processing_status == DocumentStatus.QUEUED
    assert doc.upload_batch_id == batch_id

    # 2. File stored
    stored_content = await storage_repo.get(doc.path)
    assert stored_content == content

    # 3. Job created
    # Find job for this doc_uuid in the payload
    jobs = list(job_repo._jobs.values())
    assert len(jobs) == 1
    job = jobs[0]
    assert job.job_type == "process_document"
    assert job.payload["doc_uuid"] == str(doc_uuid)
    assert job.status == JobStatus.PENDING
    assert job.correlation_id == batch_id
