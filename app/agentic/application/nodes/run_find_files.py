import logging

from app.agentic.domain.graph_state import AgentGraphState
from app.tools.application.repository_tool_service import RepositoryToolService

logger = logging.getLogger(__name__)


class RunFindFilesNode:
    """
    Executes a find_files search over the repository snapshot.
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
            "graph_node.find_files conversation_id=%s repository_id=%s "
            "query=%r extensions=%s limit=%s",
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
                + ["Failed to run find_files: Missing repo ID."],
            }

        matches = await self._tool_service.find_files(
            repository_id=repo_id,
            repository_sync_id=state["scope"].repository_sync_id,
            query=query,
            extensions=extensions,
            limit=limit,
        )

        items = [f"Found: {m.path}" for m in matches]
        tool_output = "\n".join(items) or "No files found."
        current_context = (
            (state["tool_context"] or "") + f"\n\nFind Files ({query}):\n" + tool_output
        )

        logger.info(
            "graph_node.find_files.done conversation_id=%s matches=%s",
            state["conversation_id"],
            len(matches),
        )

        return {
            "tool_context": current_context,
            "reasoning_trace": state["reasoning_trace"]
            + [f"Found {len(matches)} files."],
        }
