from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio

from app.infra.db import Database
from app.ingestion.domain.document import (
    Document,
    DocumentStatus,
    DocumentType,
    SourceType,
)
from app.ingestion.infra.postgres_chunk_repo import PostgresChunkRepo
from app.ingestion.infra.postgres_document_repo import PostgresDocumentRepo
from app.repositories.domain.repository import Repository
from app.repositories.infra.postgres_repository_repo import PostgresRepositoryRepo
from app.retrieval.application.retriever import Retriever
from app.retrieval.infra.postgres_retrieval_repo import PostgresRetrievalRepo
from app.schemas.chat import ChatScope, ScopeType


@pytest_asyncio.fixture
async def db_pool():
    # Ensure pool is open
    pool = Database.get_pool()
    await pool.open()
    yield pool
    await Database.close()


@pytest.mark.asyncio
async def test_retrieval_threshold_logic(db_pool):
    doc_repo = PostgresDocumentRepo(db_pool)
    chunk_repo = PostgresChunkRepo(db_pool)
    repo_repo = PostgresRepositoryRepo(db_pool)
    retrieval_repo = PostgresRetrievalRepo(db_pool)

    # 1. Setup: Insert a repository, a document and its chunks
    repo_id = uuid4()
    repository = Repository(
        id=repo_id,
        provider="github",
        clone_url="https://github.com/test/threshold",
        normalized_clone_url="github.com/test/threshold",
        owner="test",
        name="threshold",
        local_path="/tmp/threshold",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await repo_repo.save(repository)

    doc_uuid = uuid4()
    document = Document(
        uuid=doc_uuid,
        source_type=SourceType.UPLOAD,
        source_id="threshold.py",
        path="tests/threshold.py",
        filename="threshold.py",
        extension="py",
        doc_type=DocumentType.CODE,
        processing_status=DocumentStatus.READY,
        size_bytes=100,
        repository_id=repo_id,
        content_hash="threshold_hash",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(document)

    # Insert a chunk with a specific embedding [1, 0, ...]
    embedding = [0.0] * 1024
    embedding[0] = 1.0

    await chunk_repo.save_chunks(
        str(doc_uuid),
        [
            {
                "chunk_index": 0,
                "content": "This is a test for threshold.",
                "embedding": embedding,
                "metadata": {"foo": "bar"},
            }
        ],
    )

    scope = ChatScope(
        type=ScopeType.REPOSITORY,
        repository_id=repo_id,
    )

    # 2. Test with low threshold (should find it)
    # Cosine similarity of [1, 0...] with itself is 1.0
    mock_embedding_service = MagicMock()
    mock_embedding_service.get_embedding = AsyncMock(return_value=embedding)

    retriever_low = Retriever(
        retrieval_repo=retrieval_repo,
        embedding_service=mock_embedding_service,
        threshold=0.1,  # Very permissive
    )
    results_low = await retriever_low.retrieve("test", scope)
    assert len(results_low) == 1
    assert results_low[0].content == "This is a test for threshold."

    # 3. Test with very high threshold (should find it because similarity is 1.0)
    retriever_high = Retriever(
        retrieval_repo=retrieval_repo,
        embedding_service=mock_embedding_service,
        threshold=0.99,
    )
    results_high = await retriever_high.retrieve("test", scope)
    assert len(results_high) == 1

    # 4. Test with completely different embedding
    # Cosine similarity of [1, 0...] with [0, 1, 0...] is 0.0
    different_embedding = [0.0] * 1024
    different_embedding[1] = 1.0
    mock_embedding_service.get_embedding = AsyncMock(return_value=different_embedding)

    retriever_diff = Retriever(
        retrieval_repo=retrieval_repo,
        embedding_service=mock_embedding_service,
        threshold=0.1,
    )
    results_diff = await retriever_diff.retrieve("test", scope)
    assert len(results_diff) == 0
