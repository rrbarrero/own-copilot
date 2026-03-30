from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio

from app.conversation.domain.conversation import Conversation
from app.conversation.domain.conversation_message import ConversationMessage
from app.conversation.infra.postgres_conversation_repo import PostgresConversationRepo
from app.infra.db import Database


@pytest_asyncio.fixture
async def db_pool():
    pool = Database.get_pool()
    await pool.open()
    yield pool
    await Database.close()


@pytest.mark.asyncio
async def test_postgres_conversation_repo_lifecycle(db_pool):
    repo = PostgresConversationRepo(db_pool)

    # 1. Create a conversation
    conv_id = uuid4()
    now = datetime.now(UTC)
    conversation = Conversation(
        id=conv_id,
        scope_type="repository",
        repository_id=None,
        document_id=None,
        created_at=now,
        updated_at=now,
    )
    await repo.create(conversation)

    # 2. Get by ID
    fetched_conv = await repo.get_by_id(conv_id)
    assert fetched_conv is not None
    assert fetched_conv.id == conv_id
    assert fetched_conv.scope_type == "repository"

    # 3. Add messages
    msg1_id = uuid4()
    msg1 = ConversationMessage(
        id=msg1_id,
        conversation_id=conv_id,
        role="user",
        content="What is this repository?",
        rewritten_question=None,
        created_at=now - timedelta(seconds=1),
    )
    await repo.add_message(msg1)

    msg2_id = uuid4()
    msg2 = ConversationMessage(
        id=msg2_id,
        conversation_id=conv_id,
        role="assistant",
        content="This is a code copilot project.",
        citations_json=[{"path": "README.md"}],
        created_at=now,
    )
    await repo.add_message(msg2)

    # 4. Fetch history
    history = await repo.get_recent_messages(conv_id, limit=5)
    assert len(history) == 2
    assert history[0].role == "user"
    assert history[1].role == "assistant"


@pytest.mark.asyncio
async def test_postgres_conversation_repo_uuid_citations(db_pool):
    repo = PostgresConversationRepo(db_pool)
    conv_id = uuid4()
    document_id = uuid4()
    now = datetime.now(UTC)

    # Setup conversation
    await repo.create(
        Conversation(
            id=conv_id,
            scope_type="repository",
            repository_id=None,
            document_id=None,
            created_at=now,
            updated_at=now,
        )
    )

    # Add message with UUID in list of dicts (the tricky part for JSON serialization)
    msg = ConversationMessage(
        id=uuid4(),
        conversation_id=conv_id,
        role="assistant",
        content="Check this document.",
        # Tricky UUID here (needs str conversion during dumps)
        citations_json=[{"document_id": document_id, "path": "test.py"}],
        created_at=now,
    )

    # This should NOT raise TypeError: Object of type UUID is not JSON serializable
    await repo.add_message(msg)

    # Verify we can fetch it back (Postgres handles JSONB -> list automatically)
    history = await repo.get_recent_messages(conv_id, limit=1)
    assert len(history) == 1
    # Check for None to satisfy type checker (Pyrefly)
    assert history[0].citations_json is not None
    # Access after guard
    citations = history[0].citations_json
    assert isinstance(citations, list)
    assert citations[0]["document_id"] == str(document_id)
