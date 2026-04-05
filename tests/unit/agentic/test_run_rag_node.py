from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest

from app.agentic.application.nodes.run_rag import RunRagNode
from app.agentic.domain.graph_state import AgentGraphState
from app.retrieval.application.retriever import Retriever
from app.schemas.chat import ChatScope, ScopeType


class StubRetriever:
    def __init__(self, chunks):
        self._chunks = chunks

    async def retrieve(self, question: str, scope: ChatScope):  # noqa: ARG002
        return self._chunks


@pytest.mark.asyncio
async def test_run_rag_node_cites_raw_parent_chunk_for_summary():
    summary_chunk = SimpleNamespace(
        document_uuid=uuid4(),
        chunk_index=7,
        content="Summary of class 'MyClass': coordinates ingestion workflow.",
        path="src/sample.py",
        filename="sample.py",
        metadata={
            "chunk_kind": "summary",
            "summary_level": "class",
            "symbol_name": "MyClass",
            "parent_chunk_indexes": [2, 3],
        },
    )
    node = RunRagNode(cast(Retriever, StubRetriever([summary_chunk])))

    state: AgentGraphState = {
        "conversation_id": uuid4(),
        "original_question": "What is the responsibility of MyClass?",
        "rewritten_question": "What is the responsibility of MyClass?",
        "scope": ChatScope(type=ScopeType.REPOSITORY, repository_id=uuid4()),
        "history": [],
        "current_strategy": None,
        "tool_calls": [],
        "retrieved_context": None,
        "tool_context": None,
        "citations": cast(list[dict], []),
        "answer": None,
        "reasoning_trace": [],
        "step_count": 0,
        "done": False,
    }

    result = await node(state)

    assert result["citations"][0]["chunk_index"] == 2
    assert "[SUMMARY CLASS MyClass]" in result["retrieved_context"]
