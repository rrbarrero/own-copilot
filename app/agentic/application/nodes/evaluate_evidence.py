import logging

from app.agentic.domain.graph_state import AgentGraphState

logger = logging.getLogger(__name__)


class EvaluateEvidenceNode:
    """
    Evaluates whether the accumulated evidence is sufficient to answer the question.
    It primarily prepares the state for downstream routing decisions.
    """

    def __init__(self, max_steps: int = 4):
        self._max_steps = max_steps

    async def __call__(self, state: AgentGraphState) -> dict:
        """
        Decision is carried over to a conditional edge, but this node can perform
        some basic logic, like checking for emptiness or reach limits.
        """
        retrieved = state.get("retrieved_context") or ""
        tool_ctx = state.get("tool_context") or ""
        has_context = bool(retrieved.strip() or tool_ctx.strip())
        at_limit = state["step_count"] >= self._max_steps

        # Determine logical "done" if we are at limit or think we have enough
        # The LLM in DecideNextActionNode already suggests "answer" strategy,
        # but this node provides a deterministic safety check.

        reasoning = state["reasoning_trace"] + ["Evidence evaluated."]
        if at_limit:
            reasoning[-1] += " Limit reached."
        if not has_context:
            reasoning[-1] += " No context obtained yet."

        logger.info(
            "graph_node.evaluate conversation_id=%s step_count=%s "
            "has_context=%s current_strategy=%s done=%s",
            state["conversation_id"],
            state["step_count"],
            has_context,
            state["current_strategy"],
            at_limit or state["current_strategy"] == "answer",
        )

        return {
            "reasoning_trace": reasoning,
            "done": at_limit or state["current_strategy"] == "answer",
        }
