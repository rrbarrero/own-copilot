import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agentic.domain.graph_state import AgentGraphState

logger = logging.getLogger(__name__)


class DecideNextActionNode:
    """
    Decides the next action to take based on the current state.
    This replaces part of the ToolPicker functionality with a graph-compatible node.
    """

    SYSTEM_PROMPT = (
        "You are an orchestrator for a technical assistant. "
        "Decide the best next action to answer the user question.\n\n"
        "STRATEGIES:\n"
        "1. rag: Use this for conceptual, general or summarized questions.\n"
        "2. find_files: Use this to locate files by name or search for where things "
        "might be.\n"
        "3. read_file: Use this to read the full content of a specific file.\n"
        "4. search_in_repo: Use this for exact text or symbol search (grep) across "
        "the repo.\n"
        "5. answer: Use this ONLY when you have enough evidence to answer fully.\n\n"
        "Return ONLY a JSON object with: strategy, parameters (dict), and reasoning."
    )

    def __init__(self, llm: BaseChatModel, max_steps: int = 4):
        self._llm = llm
        self._max_steps = max_steps

    async def __call__(self, state: AgentGraphState) -> dict:
        """
        Determines the current strategy.
        """
        has_context = bool(
            (state.get("retrieved_context") or "").strip()
            or (state.get("tool_context") or "").strip()
        )
        previous_strategies = [tc["strategy"] for tc in state["tool_calls"]]

        logger.info(
            "graph_node.decide conversation_id=%s step_count=%s has_context=%s "
            "previous_strategies=%s",
            state["conversation_id"],
            state["step_count"],
            has_context,
            previous_strategies,
        )

        if not has_context and not previous_strategies:
            logger.info(
                "graph_node.decide.result conversation_id=%s strategy=rag "
                "reason=no_evidence_yet",
                state["conversation_id"],
            )
            return {
                "current_strategy": "rag",
                "tool_calls": state["tool_calls"]
                + [{"strategy": "rag", "parameters": {}}],
                "reasoning_trace": state["reasoning_trace"]
                + ["No evidence yet. Starting with semantic retrieval."],
                "step_count": state["step_count"] + 1,
            }

        if not has_context and "rag" in previous_strategies:
            logger.info(
                "graph_node.decide.result conversation_id=%s "
                "strategy=stop_no_evidence reason=rag_without_evidence",
                state["conversation_id"],
            )
            return {
                "current_strategy": "stop_no_evidence",
                "reasoning_trace": state["reasoning_trace"]
                + ["RAG produced no evidence. Stopping without another LLM call."],
            }

        if has_context:
            logger.info(
                "graph_node.decide.result conversation_id=%s strategy=answer "
                "reason=context_already_available",
                state["conversation_id"],
            )
            return {
                "current_strategy": "answer",
                "reasoning_trace": state["reasoning_trace"]
                + ["Evidence already available. Proceeding to final answer."],
            }

        if state["step_count"] >= self._max_steps:
            logger.info(
                "graph_node.decide.result conversation_id=%s strategy=answer "
                "reason=max_steps_reached",
                state["conversation_id"],
            )
            return {
                "current_strategy": "answer",
                "reasoning_trace": state["reasoning_trace"]
                + ["Max steps reached, forcing answer."],
            }

        # Build prompt considering current context
        context_status = "Available context: "
        if state["retrieved_context"]:
            context_status += "RAG context obtained. "
        if state["tool_context"]:
            context_status += "Tool results obtained. "
        if not (state["retrieved_context"] or state["tool_context"]):
            context_status += "No context obtained yet."

        history_summary = ""
        if previous_strategies:
            history_summary = "Previous actions: " + ", ".join(previous_strategies)

        prompt = (
            f"Question: {state['rewritten_question']}\n\n"
            f"Status: {context_status}\n"
            f"{history_summary}\n\n"
            "Decide the next strategy."
        )

        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await self._llm.ainvoke(messages)
        content = str(response.content).strip()

        # Clean JSON if necessary
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()

        try:
            data = json.loads(content)
            strategy = data.get("strategy", "rag")
            params = data.get("parameters", {})
            reasoning = data.get("reasoning", "Decided to use " + strategy)
        except Exception:
            strategy = "rag"
            params = {}
            reasoning = "Failed to parse LLM decision, defaulting to RAG."

        logger.info(
            "graph_node.decide.result conversation_id=%s strategy=%s "
            "parameters=%s reasoning=%r",
            state["conversation_id"],
            strategy,
            params,
            reasoning,
        )

        return {
            "current_strategy": strategy,
            "tool_calls": state["tool_calls"]
            + [{"strategy": strategy, "parameters": params}],
            "reasoning_trace": state["reasoning_trace"]
            + [f"Action: {strategy} ({reasoning})"],
            "step_count": state["step_count"] + 1,
        }
