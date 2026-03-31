import logging

from app.agentic.domain.graph_state import AgentGraphState

logger = logging.getLogger(__name__)


class StopNoEvidenceNode:
    """
    Handles cases where no sufficient evidence was found in the graph.
    """

    def __init__(self):
        pass

    async def __call__(self, state: AgentGraphState) -> dict:
        """
        Returns a polite negative answer.
        """
        logger.info(
            "graph_node.stop_no_evidence conversation_id=%s step_count=%s",
            state["conversation_id"],
            state["step_count"],
        )
        return {
            "answer": (
                "I'm sorry, I don't have enough information to answer that question."
            ),
            "reasoning_trace": state["reasoning_trace"]
            + ["Stopped due to missing evidence."],
        }
