from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.conversation.application.question_rewriter import QuestionRewriter
from app.conversation.domain.conversation_message import ConversationMessage


@pytest.mark.asyncio
async def test_rewrite_no_history():
    mock_llm = MagicMock()
    rewriter = QuestionRewriter(mock_llm)

    question = "How are you?"
    rewritten = await rewriter.rewrite(question, [])

    assert rewritten == question
    mock_llm.ainvoke.assert_not_called()


@pytest.mark.asyncio
async def test_rewrite_with_history():
    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock()
    mock_llm.ainvoke.return_value.content = "What is the capital of France?"
    rewriter = QuestionRewriter(mock_llm)

    conv_id = uuid4()
    history = [
        ConversationMessage(
            id=uuid4(), conversation_id=conv_id, role="user", content="Where is Paris?"
        ),
        ConversationMessage(
            id=uuid4(), conversation_id=conv_id, role="assistant", content="In France."
        ),
    ]

    question = "What is its capital?"
    rewritten = await rewriter.rewrite(question, history)

    assert rewritten == "What is the capital of France?"
    assert mock_llm.ainvoke.called
    prompt = mock_llm.ainvoke.call_args[0][0]
    assert "User: Where is Paris?" in prompt
    assert "Assistant: In France." in prompt
    assert "FOLLOW-UP QUESTION:\nWhat is its capital?" in prompt
