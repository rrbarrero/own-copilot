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
from app.retrieval.infra.hybrid_retrieval_service import HybridRetrievalService
from app.retrieval.infra.postgres_lexical_retrieval_provider import (
    PostgresLexicalRetrievalProvider,
)
from app.retrieval.infra.postgres_vector_retrieval_provider import (
    PostgresVectorRetrievalProvider,
)
from app.retrieval.infra.rrf_rank_fuser import RRFRankFuser
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
    retrieval_repo = HybridRetrievalService(
        vector_provider=PostgresVectorRetrievalProvider(db_pool),
        lexical_provider=PostgresLexicalRetrievalProvider(db_pool),
        rank_fuser=RRFRankFuser(),
    )

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
    results_diff = await retriever_diff.retrieve("completely_different_word", scope)
    assert len(results_diff) == 0


@pytest.mark.asyncio
async def test_retrieval_falls_back_to_lower_threshold_when_primary_returns_nothing(
    db_pool,
):
    doc_repo = PostgresDocumentRepo(db_pool)
    chunk_repo = PostgresChunkRepo(db_pool)
    repo_repo = PostgresRepositoryRepo(db_pool)
    retrieval_repo = HybridRetrievalService(
        vector_provider=PostgresVectorRetrievalProvider(db_pool),
        lexical_provider=PostgresLexicalRetrievalProvider(db_pool),
        rank_fuser=RRFRankFuser(),
    )

    repo_id = uuid4()
    repository = Repository(
        id=repo_id,
        provider="github",
        clone_url="https://github.com/test/fallback",
        normalized_clone_url="github.com/test/fallback",
        owner="test",
        name="fallback",
        local_path="/tmp/fallback",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await repo_repo.save(repository)

    doc_uuid = uuid4()
    document = Document(
        uuid=doc_uuid,
        source_type=SourceType.UPLOAD,
        source_id="fallback.py",
        path="tests/fallback.py",
        filename="fallback.py",
        extension="py",
        doc_type=DocumentType.CODE,
        processing_status=DocumentStatus.READY,
        size_bytes=100,
        repository_id=repo_id,
        content_hash="fallback_hash",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(document)

    embedding = [0.0] * 1024
    embedding[0] = 1.0

    await chunk_repo.save_chunks(
        str(doc_uuid),
        [
            {
                "chunk_index": 0,
                "content": "Fallback retrieval should still find this chunk.",
                "embedding": embedding,
                "metadata": {"foo": "bar"},
            }
        ],
    )

    scope = ChatScope(
        type=ScopeType.REPOSITORY,
        repository_id=repo_id,
    )

    mock_embedding_service = MagicMock()
    mock_embedding_service.get_embedding = AsyncMock(return_value=embedding)

    retriever = Retriever(
        retrieval_repo=retrieval_repo,
        embedding_service=mock_embedding_service,
        threshold=1.1,
        fallback_threshold=0.1,
    )

    results = await retriever.retrieve("test", scope)
    assert len(results) == 1
    assert results[0].content == "Fallback retrieval should still find this chunk."


@pytest.mark.asyncio
async def test_hybrid_search_does_not_bypass_vector_threshold_with_lexical_only_match(
    db_pool,
):
    doc_repo = PostgresDocumentRepo(db_pool)
    chunk_repo = PostgresChunkRepo(db_pool)
    repo_repo = PostgresRepositoryRepo(db_pool)
    retrieval_repo = HybridRetrievalService(
        vector_provider=PostgresVectorRetrievalProvider(db_pool),
        lexical_provider=PostgresLexicalRetrievalProvider(db_pool),
        rank_fuser=RRFRankFuser(),
    )

    repo_id = uuid4()
    repository = Repository(
        id=repo_id,
        provider="github",
        clone_url="https://github.com/test/hybrid-threshold",
        normalized_clone_url="github.com/test/hybrid-threshold",
        owner="test",
        name="hybrid-threshold",
        local_path="/tmp/hybrid-threshold",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await repo_repo.save(repository)

    doc_uuid = uuid4()
    document = Document(
        uuid=doc_uuid,
        source_type=SourceType.UPLOAD,
        source_id="hybrid_threshold.py",
        path="src/hybrid_threshold.py",
        filename="hybrid_threshold.py",
        extension="py",
        doc_type=DocumentType.CODE,
        processing_status=DocumentStatus.READY,
        size_bytes=100,
        repository_id=repo_id,
        content_hash="hybrid_threshold_hash",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(document)

    stored_embedding = [0.0] * 1024
    stored_embedding[0] = 1.0

    await chunk_repo.save_chunks(
        str(doc_uuid),
        [
            {
                "chunk_index": 0,
                "content": "def build_repo_sync_job():\n    return 'ok'\n",
                "embedding": stored_embedding,
                "metadata": {"foo": "bar"},
            }
        ],
    )

    scope = ChatScope(
        type=ScopeType.REPOSITORY,
        repository_id=repo_id,
    )

    query_embedding = [0.0] * 1024
    query_embedding[0] = 0.8
    query_embedding[1] = 0.6

    primary_results = await retrieval_repo.search(
        query_embedding=query_embedding,
        scope=scope,
        top_k=5,
        threshold=0.9,
        question="Where is build_repo_sync_job defined?",
    )
    assert primary_results == []

    fallback_results = await retrieval_repo.search(
        query_embedding=query_embedding,
        scope=scope,
        top_k=5,
        threshold=0.7,
        question="Where is build_repo_sync_job defined?",
    )
    assert len(fallback_results) == 1
    assert "build_repo_sync_job" in fallback_results[0].content


@pytest.mark.asyncio
async def test_lexical_provider_matches_code_identifiers_and_paths(db_pool):
    doc_repo = PostgresDocumentRepo(db_pool)
    chunk_repo = PostgresChunkRepo(db_pool)
    repo_repo = PostgresRepositoryRepo(db_pool)
    lexical_provider = PostgresLexicalRetrievalProvider(db_pool)

    repo_id = uuid4()
    repository = Repository(
        id=repo_id,
        provider="github",
        clone_url="https://github.com/test/code-search",
        normalized_clone_url="github.com/test/code-search",
        owner="test",
        name="code-search",
        local_path="/tmp/code-search",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await repo_repo.save(repository)

    doc_uuid = uuid4()
    document = Document(
        uuid=doc_uuid,
        source_type=SourceType.UPLOAD,
        source_id="app/factory.py",
        path="app/factory.py",
        filename="factory.py",
        extension="py",
        doc_type=DocumentType.CODE,
        processing_status=DocumentStatus.READY,
        size_bytes=100,
        repository_id=repo_id,
        content_hash="code_search_hash",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(document)

    embedding = [0.0] * 1024
    embedding[0] = 1.0

    await chunk_repo.save_chunks(
        str(doc_uuid),
        [
            {
                "chunk_index": 0,
                "content": (
                    "def build_repo_sync_job():\n    return create_retrieval_repo()\n"
                ),
                "embedding": embedding,
                "metadata": {"foo": "bar"},
            }
        ],
    )

    scope = ChatScope(
        type=ScopeType.REPOSITORY,
        repository_id=repo_id,
    )

    identifier_results = await lexical_provider.search(
        question="build_repo_sync_job",
        scope=scope,
        top_k=5,
    )
    assert len(identifier_results) == 1
    assert identifier_results[0].path == "app/factory.py"

    path_results = await lexical_provider.search(
        question="app/factory.py",
        scope=scope,
        top_k=5,
    )
    assert len(path_results) == 1
    assert path_results[0].filename == "factory.py"

    generic_results = await lexical_provider.search(
        question="What is the primary ingredient of a traditional Japanese sushi?",
        scope=scope,
        top_k=5,
    )
    assert generic_results == []
