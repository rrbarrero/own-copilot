import logging

from app.agentic.domain.graph_state import AgentGraphState
from app.conversation.application.question_rewriter import QuestionRewriter

logger = logging.getLogger(__name__)


class RewriteQuestionNode:
    def __init__(self, rewriter: QuestionRewriter):
        self._rewriter = rewriter

    async def __call__(self, state: AgentGraphState) -> dict:
        """
        Rewrites the original question into a standalone version based on history.
        """
        logger.info(
            "graph_node.rewrite conversation_id=%s history_messages=%s "
            "original_question=%r",
            state["conversation_id"],
            len(state["history"]),
            state["original_question"],
        )
        rewritten = await self._rewriter.rewrite(
            question=state["original_question"], history=state["history"]
        )

        logger.info(
            "graph_node.rewrite.done conversation_id=%s rewritten_question=%r",
            state["conversation_id"],
            rewritten,
        )

        return {
            "rewritten_question": rewritten,
            "reasoning_trace": state["reasoning_trace"] + ["Question rewritten."],
        }
