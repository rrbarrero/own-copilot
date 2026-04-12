from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.agentic.application.nodes.run_review_branch import RunReviewBranchNode
from app.schemas.chat import ChatScope, ScopeType


@pytest.mark.asyncio
async def test_run_review_branch_node_formats_findings():
    service = AsyncMock()
    service.execute.return_value = SimpleNamespace(
        base_branch="main",
        branch="feature/test",
        base_sync_id=uuid4(),
        head_sync_id=uuid4(),
        summary="One issue found.",
        findings=[
            SimpleNamespace(
                severity="high",
                title="Broken guard",
                path="app/service.py",
                rationale="Null input is no longer validated.",
                line_start=10,
                line_end=12,
            )
        ],
    )
    node = RunReviewBranchNode(service)

    state = {
        "conversation_id": uuid4(),
        "original_question": "Review branch feature/test",
        "rewritten_question": "Review branch feature/test",
        "scope": ChatScope(type=ScopeType.REPOSITORY, repository_id=uuid4()),
        "history": [],
        "current_strategy": "review_branch",
        "tool_calls": [
            {
                "strategy": "review_branch",
                "parameters": {"branch": "feature/test"},
            }
        ],
        "retrieved_context": None,
        "tool_context": None,
        "citations": [],
        "answer": None,
        "reasoning_trace": [],
        "step_count": 1,
        "done": False,
    }

    result = await node(state)

    assert "Branch review against main: feature/test" in result["answer"]
    assert "[high] Broken guard (app/service.py:10-12)" in result["answer"]
