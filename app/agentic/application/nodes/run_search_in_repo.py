import logging

from app.agentic.domain.graph_state import AgentGraphState
from app.tools.application.repository_tool_service import RepositoryToolService

logger = logging.getLogger(__name__)


class RunSearchInRepoNode:
    """
    Executes a search (grep-like) across the repository snapshot for text or symbols.
    """

    def __init__(self, tool_service: RepositoryToolService):
        self._tool_service = tool_service

    async def __call__(self, state: AgentGraphState) -> dict:
        last_tc = state["tool_calls"][-1]
        params = last_tc.get("parameters", {})
        query = params.get("query", "")
        extensions = params.get("extensions")
        limit = params.get("limit", 10)

        logger.info(
            "graph_node.search_in_repo conversation_id=%s repository_id=%s query=%r extensions=%s limit=%s",
            state["conversation_id"],
            state["scope"].repository_id,
            query,
            extensions,
            limit,
        )

        repo_id = state["scope"].repository_id
        if not repo_id:
            return {
                "tool_context": "No repository ID provided.",
                "reasoning_trace": state["reasoning_trace"]
                + ["Failed to search in repo: Missing repo ID."],
            }

        matches = await self._tool_service.search_in_repo(
            repository_id=repo_id,
            query=query,
            extensions=extensions,
            limit=limit,
        )

        items = [f"{m.path}:{m.line_number}: {m.line_content}" for m in matches]
        tool_output = "\n".join(items) or "No results found."
        current_context = (
            (state["tool_context"] or "")
            + f"\n\nSearch In Repo ({query}):\n"
            + tool_output
        )

        logger.info(
            "graph_node.search_in_repo.done conversation_id=%s matches=%s",
            state["conversation_id"],
            len(matches),
        )

        return {
            "tool_context": current_context,
            "reasoning_trace": state["reasoning_trace"]
            + [f"Search found {len(matches)} matches."],
        }
