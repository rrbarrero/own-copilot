import logging

from langchain_core.language_models import BaseChatModel

from app.agentic.domain.graph_state import AgentGraphState
from app.prompts.rag_prompt import RAG_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class AnswerFromContextNode:
    """
    Synthesizes the answer using context gathered during the graph execution.
    """

    def __init__(self, llm: BaseChatModel):
        self._llm = llm

    async def __call__(self, state: AgentGraphState) -> dict:
        """
        Synthesizes the final answer.
        """
        context = ""
        retrieved = state.get("retrieved_context") or ""
        tool_ctx = state.get("tool_context") or ""

        if retrieved.strip():
            context += "--- RAG CONTEXT ---\n" + retrieved + "\n\n"
        if tool_ctx.strip():
            context += "--- DETERMINISTIC TOOL CONTEXT ---\n" + tool_ctx + "\n\n"

        logger.info(
            "graph_node.answer conversation_id=%s has_rag_context=%s "
            "has_tool_context=%s citations=%s",
            state["conversation_id"],
            bool(retrieved.strip()),
            bool(tool_ctx.strip()),
            len(state.get("citations", [])),
        )

        if state.get("answer"):
            logger.info(
                "graph_node.answer.done conversation_id=%s "
                "result=passthrough_prepared_answer",
                state["conversation_id"],
            )
            return {
                "answer": str(state["answer"]),
                "reasoning_trace": state["reasoning_trace"]
                + ["Returned prepared answer without extra synthesis."],
            }

        if not context.strip():
            logger.info(
                "graph_node.answer.done conversation_id=%s "
                "result=deterministic_refusal",
                state["conversation_id"],
            )
            return {
                "answer": (
                    "I'm sorry, I don't have enough information "
                    "to answer that question."
                ),
                "reasoning_trace": state["reasoning_trace"]
                + ["No evidence available. Returned deterministic refusal."],
            }

        prompt = RAG_PROMPT_TEMPLATE.format(
            context=context, question=state["original_question"]
        )

        ans_res = await self._llm.ainvoke(prompt)

        logger.info(
            "graph_node.answer.done conversation_id=%s answer_preview=%r",
            state["conversation_id"],
            str(ans_res.content)[:200],
        )

        return {
            "answer": str(ans_res.content),
            "reasoning_trace": state["reasoning_trace"] + ["Final answer synthesized."],
        }
