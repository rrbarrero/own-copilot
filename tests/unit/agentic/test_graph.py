from unittest.mock import AsyncMock

import pytest

from app.agentic.infra.langgraph_builder import LangGraphBuilder


class TestLangGraphBuilder:
    @pytest.fixture
    def mock_nodes(self):
        return {
            "rewrite": AsyncMock(),
            "decide": AsyncMock(),
            "rag": AsyncMock(),
            "find_files": AsyncMock(),
            "read_file": AsyncMock(),
            "search_in_repo": AsyncMock(),
            "evaluate": AsyncMock(),
            "answer": AsyncMock(),
            "stop_no_evidence": AsyncMock(),
        }

    def test_build_graph(self, mock_nodes):
        builder = LangGraphBuilder(
            rewrite_node=mock_nodes["rewrite"],
            decide_node=mock_nodes["decide"],
            rag_node=mock_nodes["rag"],
            find_files_node=mock_nodes["find_files"],
            read_file_node=mock_nodes["read_file"],
            search_in_repo_node=mock_nodes["search_in_repo"],
            evaluate_node=mock_nodes["evaluate"],
            answer_node=mock_nodes["answer"],
            stop_no_evidence_node=mock_nodes["stop_no_evidence"],
        )
        graph = builder.build()
        assert graph is not None

        # Check nodes are registered (Internal LangGraph checks)
        # We can try to invoke with dummy state to see if it starts
        # (needs AsyncMock to return something valid though)
