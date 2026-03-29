from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio

from app.infra.db import Database
from app.ingestion.domain.document import (
    Document,
    DocumentType,
    ProcessingStatus,
    SourceType,
)
from app.ingestion.infra.postgres_chunk_repo import PostgresChunkRepo
from app.ingestion.infra.postgres_document_repo import PostgresDocumentRepo
from app.repositories.domain.repository import Repository
from app.repositories.infra.postgres_repository_repo import PostgresRepositoryRepo
from app.retrieval.application.chat_with_citations import ChatWithCitations
from app.retrieval.application.retriever import Retriever
from app.retrieval.infra.postgres_retrieval_repo import PostgresRetrievalRepo
from app.schemas.chat import ChatRequest, ChatScope, ScopeType


@pytest_asyncio.fixture
async def db_pool():
    # Ensure pool is open
    pool = Database.get_pool()
    await pool.open()
    yield pool
    await Database.close()


@pytest.mark.asyncio
async def test_chat_with_citations_integration(db_pool):
    doc_repo = PostgresDocumentRepo(db_pool)
    chunk_repo = PostgresChunkRepo(db_pool)
    repo_repo = PostgresRepositoryRepo(db_pool)
    retrieval_repo = PostgresRetrievalRepo(db_pool)

    # 1. Setup: Insert a repository, a document and its chunks
    repo_id = uuid4()
    repository = Repository(
        id=repo_id,
        provider="github",
        clone_url="https://github.com/test/repo",
        normalized_clone_url="github.com/test/repo",
        owner="test",
        name="repo",
        local_path="/tmp/test",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await repo_repo.save(repository)

    doc_uuid = uuid4()
    document = Document(
        uuid=doc_uuid,
        source_type=SourceType.UPLOAD,
        source_id="test.py",
        path="tests/test.py",
        filename="test.py",
        extension="py",
        doc_type=DocumentType.CODE,
        processing_status=ProcessingStatus.INDEXED,
        size_bytes=100,
        repository_id=repo_id,
        content_hash="hash123",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(document)

    # Insert a chunk with a specific embedding
    embedding = [0.0] * 1024
    embedding[0] = 1.0

    await chunk_repo.save_chunks(
        str(doc_uuid),
        [
            {
                "chunk_index": 0,
                "content": "This is a secret code about bananas.",
                "embedding": embedding,
                "metadata": {"foo": "bar"},
            }
        ],
    )

    # 2. Mocks for LLM and Embeddings
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()
    mock_llm.ainvoke.return_value.content = "The secret is bananas."

    mock_embedding_service = MagicMock()
    mock_embedding_service.get_embedding = AsyncMock(return_value=embedding)

    # 3. Create Service
    retriever = Retriever(
        retrieval_repo=retrieval_repo,
        embedding_service=mock_embedding_service,
        top_k=1,
    )
    service = ChatWithCitations(
        retriever=retriever,
        llm=mock_llm,
    )

    # 4. Execute Chat Request
    request = ChatRequest(
        question="What is the secret code?",
        scope=ChatScope(
            type=ScopeType.REPOSITORY,
            repository_id=repo_id,
        ),
    )

    response = await service.chat(request)

    # 5. Assertions
    assert response.answer == "The secret is bananas."
    assert len(response.citations) == 1
    assert response.citations[0].document_id == doc_uuid
    assert response.citations[0].path == "tests/test.py"
    assert response.citations[0].chunk_index == 0

    # Verify that we searched with the right scope
    mock_embedding_service.get_embedding.assert_called_with("What is the secret code?")
    assert mock_llm.ainvoke.called
    prompt_sent = mock_llm.ainvoke.call_args[0][0]
    assert "bananas" in prompt_sent
    assert "What is the secret code?" in prompt_sent
