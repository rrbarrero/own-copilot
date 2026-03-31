import asyncio
import os

import pytest
import pytest_asyncio

from app.factory import (
    create_chat_service,
    create_document_repo,
    create_repository_sync_repo,
    create_request_repository_sync,
)
from app.infra.db import Database
from app.ingestion.domain.document import DocumentStatus
from app.repositories.domain.repository_sync import RepositorySyncStatus
from app.schemas.chat import ChatRequest, ChatScope, ScopeType


@pytest_asyncio.fixture
async def db_pool_e2e():
    """
    Independent fixture for E2E tests to ensure we don't interfere
    with mocks from other tests.
    """
    if os.environ.get("TESTING") != "true":
        pytest.skip("E2E tests require TESTING=true to avoid data loss.")

    pool = Database.get_pool()
    await pool.open()
    yield pool
    await Database.close()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_repo_sync_and_chat_e2e(db_pool_e2e):
    """
    E2E Test to reproduce the full workflow:
    1. Register and sync a repository through the application layer.
    2. Wait for the background worker to finish sync and indexing.
    3. Ask a question about the repository using the RAG ChatService.
    4. Assertions on the response and citations.

    IMPORTANT: This test requires a running worker and a reachable Ollama instance.
    It takes significant time as it performs real LLM and Embedding operations.
    """
    # Acknowledge the fixture to satisfy Ruff ARG001
    assert db_pool_e2e is not None

    repo_url = "https://github.com/rrbarrero/own-copilot.git"
    sync_service = create_request_repository_sync()
    sync_repo = create_repository_sync_repo()
    doc_repo = create_document_repo()
    chat_service = create_chat_service()

    # 1. Start Sync
    result = await sync_service.execute(clone_url=repo_url)
    repo_id = result.repository_id
    assert repo_id is not None
    assert result.status == "queued"

    # 2. Wait for Sync to complete
    sync_completed = False
    timeout = 360  # 6 minutes
    interval = 10
    elapsed = 0

    print(f"\nWaiting for repository sync {repo_id} to complete...")
    while elapsed < timeout:
        last_sync = await sync_repo.get_latest_by_repository_id(repo_id)
        if last_sync:
            if last_sync.status == RepositorySyncStatus.COMPLETED:
                sync_completed = True
                print(f"Sync completed in {elapsed}s.")
                break
            if last_sync.status == RepositorySyncStatus.FAILED:
                pytest.fail(f"Sync failed for repository: {last_sync.last_error}")

        await asyncio.sleep(interval)
        elapsed += interval

    if not sync_completed:
        pytest.fail(f"Sync timed out after {timeout}s.")

    # 3. Wait for documents to be indexed (status ready)
    docs_ready = False
    elapsed = 0
    print("Waiting for documents to be indexed (status READY)...")
    while elapsed < timeout:
        docs = await doc_repo.list_by_repository_id(repo_id)
        if docs:
            ready_docs = [
                d for d in docs if d.processing_status == DocumentStatus.READY
            ]
            if len(ready_docs) > 0:
                print(
                    f"Found {len(ready_docs)} ready documents "
                    f"in {len(docs)} total docs."
                )
                docs_ready = True
                break

        await asyncio.sleep(interval)
        elapsed += interval

    if not docs_ready:
        pytest.fail(f"Document indexing timed out after {timeout}s.")

    # 4. Perform Chat Request
    question = "Explain the responsibility of the IngestionService."
    request = ChatRequest(
        question=question,
        scope=ChatScope(
            type=ScopeType.REPOSITORY,
            repository_id=repo_id,
        ),
    )

    print(f"\nSending chat request: {question}")
    response = await chat_service.chat(request)

    # 5. Final Assertions
    assert response.answer is not None
    assert len(response.answer) > 20
    assert response.conversation_id is not None

    print(f"\nAssistant Answer: {response.answer}")
    print("\nCitations:")
    for cite in response.citations:
        print(f" - {cite.filename} in {cite.path}")

    # Check if we got citations from the repo
    assert len(response.citations) > 0
    citation_files = [c.filename for c in response.citations]

    # Core files we expect to see cited given the question
    target_files = [
        "01-overview.md",
        "02-architecture.md",
        "factory.py",
    ]
    found_targets = [f for f in target_files if f in citation_files]
    print(f"Found targeted citations: {found_targets}")

    # Expect code citations given the technical question.
    assert len(found_targets) > 0 or any(".py" in f for f in citation_files)

    # 6. Verify "I don't know" handling
    out_of_context_question = (
        "What is the primary ingredient of a traditional Japanese sushi?"
    )
    print(f"\nSending out-of-context request: {out_of_context_question}")

    request_no_info = ChatRequest(
        question=out_of_context_question,
        scope=ChatScope(
            type=ScopeType.REPOSITORY,
            repository_id=repo_id,
        ),
    )
    response_no_info = await chat_service.chat(request_no_info)

    print(f"Assistant Negative Answer: {response_no_info.answer}")

    # Assert that the model follows the prompt's instruction to refuse
    refusal_keywords = ["I'm sorry", "don't have", "enough information"]
    assert any(kw.lower() in response_no_info.answer.lower() for kw in refusal_keywords)

    # CRITICAL: Even if the retriever found some noise, the LLM MUST NOT
    # answer from internal knowledge (e.g. knowing Paris is the capital).
    assert "Paris" not in response_no_info.answer
    assert (
        "France" not in response_no_info.answer
        or "I'm sorry" in response_no_info.answer
    )

    # We allow some noise citations at 0.5 threshold, but grounded
    assert len(response_no_info.citations) < 3
