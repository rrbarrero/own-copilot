from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.conversation.domain.conversation import Conversation
from app.schemas.chat import ChatRequest, ChatResponse, ChatScope, ScopeType
from app.tools.application.tool_aware_chat_service import ToolAwareChatService


@pytest.mark.asyncio
async def test_tool_aware_chat_service_reuses_same_conversation_on_rag_fallback():
    stored_conversations: dict = {}
    repository_id = uuid4()
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(
        side_effect=lambda conversation_id: stored_conversations.get(conversation_id)
    )
    mock_repo.create = AsyncMock(
        side_effect=lambda conversation: stored_conversations.setdefault(
            conversation.id, conversation
        )
    )
    mock_repo.get_recent_messages = AsyncMock(return_value=[])
    mock_repo.add_message = AsyncMock()

    mock_rewriter = MagicMock()
    mock_rewriter.rewrite = AsyncMock(side_effect=lambda question, *_a, **_k: question)

    rag_response = ChatResponse(
        conversation_id=uuid4(),
        answer="RAG answer",
        citations=[],
    )
    mock_rag = MagicMock()
    mock_rag.chat = AsyncMock(return_value=rag_response)

    mock_tool_service = MagicMock()
    mock_llm = MagicMock()
    service = ToolAwareChatService(
        conversation_repo=mock_repo,
        question_rewriter=mock_rewriter,
        chat_with_citations=mock_rag,
        tool_service=mock_tool_service,
        llm=mock_llm,
    )
    service._tool_picker = MagicMock()
    service._tool_picker.decide = AsyncMock(
        return_value=type("Decision", (), {"strategy": "rag", "parameters": {}})()
    )

    request = ChatRequest(
        question="Explain ingestion",
        scope=ChatScope(
            type=ScopeType.REPOSITORY,
            repository_id=repository_id,
        ),
    )

    response = await service.chat(request)

    assert response.conversation_id in stored_conversations
    assert mock_repo.create.call_count == 1
    assert mock_repo.get_by_id.call_count == 1
    assert mock_rag.chat.await_count == 1


@pytest.mark.asyncio
async def test_tool_aware_chat_service_prompt_keeps_question_language():
    conversation = Conversation(
        id=uuid4(),
        scope_type=ScopeType.REPOSITORY,
        repository_id=uuid4(),
        document_id=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=conversation)
    mock_repo.create = AsyncMock()
    mock_repo.get_recent_messages = AsyncMock(return_value=[])
    mock_repo.add_message = AsyncMock()

    mock_rewriter = MagicMock()
    mock_rewriter.rewrite = AsyncMock(side_effect=lambda question, *_a, **_k: question)

    mock_rag = MagicMock()
    mock_tool_service = MagicMock()
    mock_tool_service.find_files = AsyncMock(return_value=[])

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()
    mock_llm.ainvoke.return_value.content = "respuesta"

    service = ToolAwareChatService(
        conversation_repo=mock_repo,
        question_rewriter=mock_rewriter,
        chat_with_citations=mock_rag,
        tool_service=mock_tool_service,
        llm=mock_llm,
    )
    service._tool_picker = MagicMock()
    service._tool_picker.decide = AsyncMock(
        return_value=type(
            "Decision",
            (),
            {"strategy": "find_files", "parameters": {"query": "factory"}},
        )()
    )

    request = ChatRequest(
        question="Busca factory.py",
        scope=ChatScope(
            type=ScopeType.REPOSITORY,
            repository_id=conversation.repository_id,
        ),
    )

    await service.chat(request)

    assert mock_llm.ainvoke.await_count == 1
    called_messages = mock_llm.ainvoke.call_args.args[0]
    prompt = called_messages[0].content
    assert "same language as the question." in prompt
    assert "(English)" not in prompt
