from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agentic.application.graph_chat_service import GraphChatService
from app.agentic.application.nodes.answer_from_context import (
    AnswerFromContextNode,
)
from app.agentic.application.nodes.decide_next_action import (
    DecideNextActionNode,
)
from app.agentic.application.nodes.evaluate_evidence import (
    EvaluateEvidenceNode,
)
from app.agentic.application.nodes.rewrite_question import RewriteQuestionNode
from app.agentic.application.nodes.run_find_files import RunFindFilesNode
from app.agentic.application.nodes.run_rag import RunRagNode
from app.agentic.application.nodes.run_read_file import RunReadFileNode
from app.agentic.application.nodes.run_search_in_repo import (
    RunSearchInRepoNode,
)
from app.agentic.application.nodes.stop_no_evidence import StopNoEvidenceNode
from app.agentic.infra.langgraph_builder import LangGraphBuilder
from app.schemas.chat import ChatRequest, ChatScope, ScopeType


@pytest.mark.asyncio
async def test_graph_chat_service_logic():
    # Mock dependencies
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)
    mock_repo.get_messages = AsyncMock(return_value=[])
    mock_repo.get_recent_messages = AsyncMock(return_value=[])
    mock_repo.create = AsyncMock()
    mock_repo.add_message = AsyncMock()
    mock_repo.save_message = AsyncMock()

    mock_llm = AsyncMock()

    m_final_ans = MagicMock()
    m_final_ans.content = "BANANAS ARE YELLOW."

    mock_llm.ainvoke.side_effect = [m_final_ans]

    from uuid import uuid4
    mock_retriever = AsyncMock()
    # Return matched context as a real object or mock with real primitives
    chunk = MagicMock()
    chunk.content = "Found context about bananas."
    chunk.filename = "test.py"
    chunk.document_uuid = uuid4()
    chunk.path = "src/test.py"
    chunk.chunk_index = 0
    
    mock_retriever.retrieve.return_value = [chunk]

    mock_tool_service = MagicMock()

    # Mock Rewriter
    mock_rewriter = MagicMock()
    mock_rewriter.rewrite = AsyncMock(return_value="Rewritten: Context")

    # Build graph with mocks
    builder = LangGraphBuilder(
        rewrite_node=RewriteQuestionNode(mock_rewriter),
        decide_node=DecideNextActionNode(mock_llm),
        rag_node=RunRagNode(mock_retriever),
        find_files_node=RunFindFilesNode(mock_tool_service),
        read_file_node=RunReadFileNode(mock_tool_service),
        search_in_repo_node=RunSearchInRepoNode(mock_tool_service),
        evaluate_node=EvaluateEvidenceNode(),
        answer_node=AnswerFromContextNode(mock_llm),
        stop_no_evidence_node=StopNoEvidenceNode(),
    )
    graph = builder.build()

    service = GraphChatService(
        conversation_repo=mock_repo, graph=graph, history_limit=5
    )

    request = ChatRequest(
        question="What is the context?",
        scope=ChatScope(type=ScopeType.REPOSITORY),
    )

    response = await service.chat(request)

    assert response.answer is not None
    assert mock_repo.add_message.call_count == 2
    assert mock_llm.ainvoke.call_count == 1
