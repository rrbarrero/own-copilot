import pytest

from app.factory import create_chat_service
from app.schemas.chat import ChatRequest, ChatScope, ScopeType


@pytest.mark.e2e
@pytest.mark.shared_ingestion
@pytest.mark.asyncio
async def test_full_repo_sync_and_chat_e2e(shared_indexed_repo):
    """
    E2E Test to reproduce the full workflow:
    1. Reuse a repository already synced and indexed for this test session.
    2. Ask a question about the repository using the RAG ChatService.
    3. Assertions on the response and citations.

    IMPORTANT: This test requires a running worker and a reachable Ollama instance.
    It performs real LLM and Embedding operations during shared setup.
    """
    chat_service = create_chat_service()
    repo_id = shared_indexed_repo.repository_id

    # 1. Perform Chat Request
    question = "What is this project about?"
    request = ChatRequest(
        question=question,
        scope=ChatScope(
            type=ScopeType.REPOSITORY,
            repository_id=repo_id,
        ),
    )

    print(f"\nSending chat request: {question}")
    response = await chat_service.chat(request)

    # 2. Final Assertions
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
        "README.md",
        "requirements.txt",
        "main.py",
        "app.py",
    ]
    found_targets = [f for f in target_files if f in citation_files]
    print(f"Found targeted citations: {found_targets}")

    # Expect citations from common project documentation or Python sources.
    assert len(found_targets) > 0 or any(
        f.endswith(".py") or f.endswith(".md") for f in citation_files
    )

    # 3. Verify "I don't know" handling
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
