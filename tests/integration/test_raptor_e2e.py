import json

import pytest

from app.factory import create_chat_service
from app.infra.db import Database
from app.schemas.chat import ChatRequest, ChatScope, ScopeType


@pytest.mark.e2e
@pytest.mark.shared_ingestion
@pytest.mark.asyncio
async def test_raptor_summarization_e2e(shared_indexed_repo):
    """
    E2E Test to verify RAPTOR:
    1. Reuse a repository already synced and indexed for this test session.
    2. Verify that summary chunks were created in the database.
    3. Perform an abstract query and verify that summaries are retrieved.
    """
    chat_service = create_chat_service()
    repo_id = shared_indexed_repo.repository_id
    pool = Database.get_pool()

    # 1. Verify RAPTOR chunks in database
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """
                SELECT metadata FROM document_chunks dc
                JOIN documents d ON d.uuid = dc.document_uuid
                WHERE d.repository_id = %s
                AND dc.metadata->>'chunk_kind' = 'summary'
                """,
            (str(repo_id),),
        )
        summary_rows = await cur.fetchall()

        print(f"\nFound {len(summary_rows)} summary chunks in DB.")
        assert len(summary_rows) > 0, "No RAPTOR summary chunks found in database!"

        # Check a sample for correct metadata
        sample_metadata = summary_rows[0][0]
        if isinstance(sample_metadata, str):
            sample_metadata = json.loads(sample_metadata)

        assert sample_metadata["source_strategy"] == "raptor"
        assert "summary_level" in sample_metadata

    # 2. Perform an abstract Chat Request to trigger RAPTOR bias
    question = "Give me a high-level overview of the project architecture."
    request = ChatRequest(
        question=question,
        scope=ChatScope(
            type=ScopeType.REPOSITORY,
            repository_id=repo_id,
        ),
    )

    print(f"\nSending RAPTOR-targeted chat request: {question}")
    response = await chat_service.chat(request)

    # 3. Final Assertions
    assert response.answer is not None
    assert len(response.answer) > 50

    # We expect some python file to be cited
    python_citations = [c for c in response.citations if ".py" in c.filename]
    assert len(python_citations) > 0, "No Python files cited in RAPTOR-targeted query"

    print(f"\nAssistant Answer (RAPTOR-powered): {response.answer}")
    for cite in response.citations:
        print(f" - {cite.filename} in {cite.path}")
