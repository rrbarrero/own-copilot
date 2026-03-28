import os
import shutil
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import psycopg_pool
import pytest

from app.ingestion.domain.document import DocumentType
from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.infra.postgres_document_repo import PostgresDocumentRepo
from app.ingestion.infra.postgres_job_repo import PostgresJobRepo
from app.repositories.application.request_repository_sync import RequestRepositorySync
from app.repositories.domain.git_repository_service_proto import CheckoutInfo
from app.repositories.domain.repository_sync import RepositorySyncStatus
from app.repositories.infra.postgres_repository_repo import PostgresRepositoryRepo
from app.repositories.infra.postgres_repository_sync_repo import (
    PostgresRepositorySyncRepo,
)
from app.repositories.infra.repository_scanner import ScannedRepositoryFile
from app.worker.application.job_handlers.sync_repository_handler import (
    SyncRepositoryJobHandler,
)


@pytest.fixture
def db_url():
    return os.environ.get(
        "DATABASE_URL", "postgres://postgres:postgres@db:5432/postgres?sslmode=disable"
    )


@pytest.mark.asyncio
async def test_full_repo_sync_orchestration_flow(db_url):
    """
    Integration test for the entire repository synchronization orchestration.
    """
    # Create mock-repo directory and files to avoid FileNotFoundError in handler
    mock_repo_path = "/tmp/mock-repo"
    os.makedirs(mock_repo_path, exist_ok=True)
    with open(f"{mock_repo_path}/file1.txt", "w") as f:
        f.write("content1")
    with open(f"{mock_repo_path}/file2.txt", "w") as f:
        f.write("content2")

    async with psycopg_pool.AsyncConnectionPool(db_url) as pool:
        repo_repo = PostgresRepositoryRepo(pool)
        sync_repo = PostgresRepositorySyncRepo(pool)
        doc_repo = PostgresDocumentRepo(pool)
        job_repo = PostgresJobRepo(pool)

        # 1. Test RequestRepositorySync
        mock_normalizer = MagicMock()

        # Use a real object instead of MagicMock with attributes to be safer
        class MockUrlInfo:
            normalized_url = "https://github.com/mock/repo"
            owner = "mock"
            name = "repo"

        mock_normalizer.normalize.return_value = MockUrlInfo()

        service = RequestRepositorySync(
            repository_repo=repo_repo,
            job_repo=job_repo,
            url_normalizer=mock_normalizer,
            checkouts_root="/tmp/checkouts",
        )

        result = await service.execute("https://github.com/mock/repo")
        assert result.status == "queued"

        saved_repo = await repo_repo.get_by_id(result.repository_id)
        assert saved_repo is not None

        saved_job = await job_repo.get_by_id(result.job_id)
        assert saved_job is not None

        # 2. Setup mock scanner and git service
        git_service = AsyncMock()
        git_service.ensure_checkout.return_value = CheckoutInfo(
            local_path=mock_repo_path,
            branch="main",
            commit_sha="sha123",
        )

        scanner = MagicMock()
        file1 = ScannedRepositoryFile(
            relative_path="file1.txt",
            absolute_path=f"{mock_repo_path}/file1.txt",
            filename="file1.txt",
            extension="txt",
            doc_type=DocumentType.TEXT,
            size_bytes=len("content1"),
            content_hash="h1",
        )
        scanner.scan.return_value = iter([file1])  # Scanner returns an iterator

        processing_service = AsyncMock()
        storage_repo = AsyncMock()

        handler = SyncRepositoryJobHandler(
            repository_repo=repo_repo,
            sync_repo=sync_repo,
            git_service=git_service,
            scanner=scanner,
            document_repo=doc_repo,
            storage_repo=storage_repo,
            processing_service=processing_service,
        )

        # 3. First Sync (All New)
        await handler.handle(saved_job)

        syncs = await sync_repo.list_by_repository_id(saved_repo.id)
        assert len(syncs) == 1
        assert syncs[0].status == RepositorySyncStatus.COMPLETED

        docs = await doc_repo.list_by_repository_id(saved_repo.id)
        assert len(docs) == 1
        assert docs[0].source_id == "file1.txt"

        # 4. Second Sync (One Updated, One New)
        file2 = ScannedRepositoryFile(
            relative_path="file2.txt",
            absolute_path=f"{mock_repo_path}/file2.txt",
            filename="file2.txt",
            extension="txt",
            doc_type=DocumentType.TEXT,
            size_bytes=len("content2"),
            content_hash="h2",
        )
        file1_updated = ScannedRepositoryFile(
            relative_path="file1.txt",
            absolute_path=f"{mock_repo_path}/file1.txt",
            filename="file1.txt",
            extension="txt",
            doc_type=DocumentType.TEXT,
            size_bytes=len("content1"),
            content_hash="h1-updated",
        )

        scanner.scan.return_value = iter([file1_updated, file2])

        sync_job_2 = Job(
            id=uuid.uuid4(),
            queue_name="ingestion",
            job_type="sync_repository",
            payload={"repository_id": str(saved_repo.id)},
            status=JobStatus.PENDING,
            attempts=0,
            max_attempts=3,
            run_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            priority=0,
        )

        await handler.handle(sync_job_2)

        docs_after = await doc_repo.list_by_repository_id(saved_repo.id)
        assert len(docs_after) == 2

        doc1 = next(d for d in docs_after if d.source_id == "file1.txt")
        assert doc1.content_hash == "h1-updated"

        # 5. Third Sync (Deletion)
        scanner.scan.return_value = iter([file2])
        sync_job_3 = Job(
            id=uuid.uuid4(),
            queue_name="ingestion",
            job_type="sync_repository",
            payload={"repository_id": str(saved_repo.id)},
            status=JobStatus.PENDING,
            attempts=0,
            max_attempts=3,
            run_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            priority=0,
        )

        await handler.handle(sync_job_3)

        docs_final = await doc_repo.list_by_repository_id(saved_repo.id)
        assert len(docs_final) == 1
        assert docs_final[0].source_id == "file2.txt"

        syncs_all = await sync_repo.list_by_repository_id(saved_repo.id)
        latest_sync = max(syncs_all, key=lambda s: s.created_at)
        assert latest_sync.deleted_files == 1

    # Clean up
    shutil.rmtree(mock_repo_path)
