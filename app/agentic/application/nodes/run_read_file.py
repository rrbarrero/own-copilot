import logging

from app.agentic.domain.graph_state import AgentGraphState
from app.tools.application.repository_tool_service import RepositoryToolService

logger = logging.getLogger(__name__)


class RunReadFileNode:
    """
    Executes a read_file operation to inspect the content of a specific file.
    """

    def __init__(self, tool_service: RepositoryToolService):
        self._tool_service = tool_service

    async def __call__(self, state: AgentGraphState) -> dict:
        last_tc = state["tool_calls"][-1]
        params = last_tc.get("parameters", {})
        path = params.get("path", "")

        logger.info(
            "graph_node.read_file conversation_id=%s repository_id=%s path=%r",
            state["conversation_id"],
            state["scope"].repository_id,
            path,
        )

        repo_id = state["scope"].repository_id
        if not repo_id:
            return {
                "tool_context": "No repository ID provided.",
                "reasoning_trace": state["reasoning_trace"]
                + ["Failed to read file: Missing repo ID."],
            }

        try:
            read_res = await self._tool_service.read_file(
                repository_id=repo_id, path=path
            )
            tool_output = f"Content of {read_res.path}:\n\n{read_res.content}"
            if len(tool_output) > 8000:
                tool_output = tool_output[:8000] + "\n\n[CONTENT TRUNCATED]"
            logger.info(
                "graph_node.read_file.done conversation_id=%s path=%r "
                "size_bytes=%s truncated=%s",
                state["conversation_id"],
                read_res.path,
                read_res.size_bytes,
                read_res.truncated,
            )
        except Exception as e:
            tool_output = f"Error reading {path}: {str(e)}"
            logger.warning(
                "graph_node.read_file.error conversation_id=%s path=%r error=%r",
                state["conversation_id"],
                path,
                str(e),
            )
        current_context = (
            (state["tool_context"] or "") + f"\n\nRead File ({path}):\n" + tool_output
        )

        return {
            "tool_context": current_context,
            "reasoning_trace": state["reasoning_trace"] + [f"Read file: {path}"],
        }
