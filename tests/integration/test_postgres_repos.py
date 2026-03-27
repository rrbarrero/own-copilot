import os
from datetime import UTC, datetime
from uuid import uuid4

import psycopg_pool
import pytest

from app.ingestion.domain.document import (
    Document,
    DocumentType,
    ProcessingStatus,
    SourceType,
)
from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.infra.postgres_document_repo import PostgresDocumentRepo
from app.ingestion.infra.postgres_job_repo import PostgresJobRepo


@pytest.fixture
def db_url():
    return os.environ.get(
        "DATABASE_URL", 
        "postgres://postgres:postgres@db:5432/postgres?sslmode=disable"
    )

@pytest.mark.asyncio
async def test_postgres_document_repo(db_url):
    # Instantiate a fresh connection pool specifically for this test function's
    # event loop
    async with psycopg_pool.AsyncConnectionPool(db_url) as pool:
        repo = PostgresDocumentRepo(pool)

        doc_id = uuid4()
        batch_id = uuid4()
        now = datetime.now(UTC)

        # 1. Test Save Document
        doc = Document(
            uuid=doc_id,
            source_type=SourceType.UPLOAD,
            source_id="test1",
            path="test/path",
            filename="test.txt",
            extension="txt",
            doc_type=DocumentType.TEXT,
            processing_status=ProcessingStatus.PENDING,
            size_bytes=1024,
            created_at=now,
            updated_at=now,
            upload_batch_id=batch_id
        )
        await repo.save(doc)

        # 2. Test Get by UUID
        saved_doc = await repo.get_by_uuid(str(doc_id))
        assert saved_doc is not None
        assert saved_doc.uuid == doc_id
        assert saved_doc.filename == "test.txt"
        assert saved_doc.size_bytes == 1024
        assert saved_doc.upload_batch_id == batch_id

        # 3. Test Get by Batch ID
        docs_in_batch = await repo.get_by_batch_id(batch_id)
        assert len(docs_in_batch) == 1
        assert docs_in_batch[0].uuid == doc_id

        # 4. Test Save Chunks (Idempotency and Insertion)
        chunks = [
            {
                "chunk_index": 0,
                "content": "hello",
                "embedding": None,
                "metadata": {"page": 1},
            },
            {
                "chunk_index": 1,
                "content": "world",
                "embedding": [0.1] * 1024,
                "metadata": {"page": 2},
            },
        ]

        await repo.save_chunks(str(doc_id), chunks)
        
        # Run twice to test idempotency (should not duplicate)
        await repo.save_chunks(str(doc_id), chunks)

        # Verify directly via DB
        async with pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                "SELECT count(*) FROM document_chunks WHERE document_uuid = %s",
                (str(doc_id),),
            )
            row = await cur.fetchone()
            assert row[0] == 2

@pytest.mark.asyncio
async def test_postgres_job_repo(db_url):
    async with psycopg_pool.AsyncConnectionPool(db_url) as pool:
        repo = PostgresJobRepo(pool)

        job_id = uuid4()
        now = datetime.now(UTC)
        payload = {"doc_uuid": "123-abc", "extra": "data"}

        # 1. Test Save Job
        job = Job(
            id=job_id,
            queue_name="integration_test",
            job_type="test_job",
            payload=payload,
            status=JobStatus.PENDING,
            attempts=0,
            max_attempts=3,
            run_at=now,
            created_at=now,
            updated_at=now,
            priority=0
        )
        await repo.save(job)

        # 2. Test Get by ID
        saved_job = await repo.get_by_id(job_id)
        assert saved_job is not None
        assert saved_job.id == job_id
        assert saved_job.queue_name == "integration_test"
        assert isinstance(saved_job.payload, dict)
        assert saved_job.payload["doc_uuid"] == "123-abc"
        assert saved_job.payload["extra"] == "data"
        assert saved_job.status == JobStatus.PENDING

        # 3. Test Claim Next Job
        claimed_job = await repo.claim_next_job("integration_test", "test_worker_1")
        assert claimed_job is not None
        assert claimed_job.id == job_id
        assert claimed_job.status == JobStatus.PROCESSING
        assert claimed_job.attempts == 1
        assert claimed_job.locked_by == "test_worker_1"

        # Next claim should fail because it is now PROCESSING
        second_claim = await repo.claim_next_job("integration_test", "test_worker_1")
        assert second_claim is None
