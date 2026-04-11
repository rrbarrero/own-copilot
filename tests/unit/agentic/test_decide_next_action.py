from uuid import uuid4

import pytest
from unittest.mock import AsyncMock

from app.agentic.application.nodes.decide_next_action import DecideNextActionNode
from app.schemas.chat import ChatScope, ScopeType


@pytest.mark.asyncio
async def test_decide_next_action_detects_review_branch_request():
    node = DecideNextActionNode(llm=AsyncMock())

    state = {
        "conversation_id": uuid4(),
        "original_question": "Haz una review de la rama feature/test",
        "rewritten_question": "Haz una review de la rama feature/test",
        "scope": ChatScope(type=ScopeType.REPOSITORY, repository_id=uuid4()),
        "history": [],
        "current_strategy": None,
        "tool_calls": [],
        "retrieved_context": None,
        "tool_context": None,
        "citations": [],
        "answer": None,
        "reasoning_trace": [],
        "step_count": 0,
        "done": False,
    }

    result = await node(state)

    assert result["current_strategy"] == "review_branch"
    assert result["tool_calls"][-1]["parameters"]["branch"] == "feature/test"
