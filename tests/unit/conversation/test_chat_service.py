from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.conversation.application.chat_service import ChatService
from app.conversation.domain.conversation import Conversation
from app.schemas.chat import ChatRequest, ChatResponse, ChatScope, ScopeType


@pytest.mark.asyncio
async def test_chat_service_new_conversation():
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)
    mock_repo.create = AsyncMock()
    mock_repo.get_recent_messages = AsyncMock(return_value=[])
    mock_repo.add_message = AsyncMock()

    mock_rewriter = MagicMock()
    # Correctly handle all positional and keyword arguments for rewrite mock
    # to avoid ruff unused arg errors by prefixing with underscore.
    mock_rewriter.rewrite = AsyncMock(
        side_effect=lambda question, *_args, **_kwargs: question
    )

    # Mock ChatWithCitations
    mock_rag_response = ChatResponse(
        conversation_id=uuid4(), answer="I am an assistant.", citations=[]
    )
    mock_rag = MagicMock()
    mock_rag.chat = AsyncMock(return_value=mock_rag_response)

    service = ChatService(mock_repo, mock_rewriter, mock_rag)

    request = ChatRequest(
        question="Hello",
        scope=ChatScope(type=ScopeType.REPOSITORY, repository_id=uuid4()),
    )

    response = await service.chat(request)

    assert response.answer == "I am an assistant."
    assert mock_repo.create.called
    assert mock_repo.add_message.call_count == 2
    assert response.conversation_id is not None


@pytest.mark.asyncio
async def test_chat_service_scope_mismatch():
    mock_repo = MagicMock()
    existing_repo_id = uuid4()
    conv = Conversation(
        id=uuid4(),
        scope_type=ScopeType.REPOSITORY,
        repository_id=existing_repo_id,
        document_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_repo.get_by_id = AsyncMock(return_value=conv)

    service = ChatService(mock_repo, MagicMock(), MagicMock())

    request = ChatRequest(
        conversation_id=conv.id,
        question="Hello",
        scope=ChatScope(type=ScopeType.REPOSITORY, repository_id=uuid4()),
    )

    with pytest.raises(HTTPException) as exc:
        await service.chat(request)
    assert exc.value.status_code == 409
    assert "Repository ID mismatch" in exc.value.detail
