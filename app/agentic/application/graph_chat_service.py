
import logging

from langchain_core.runnables import Runnable

from app.agentic.domain.graph_state import AgentGraphState
from app.conversation.application.chat_service import ChatService
from app.conversation.domain.conversation_repo_proto import ConversationRepoProto
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


class GraphChatService(ChatService):
    """
    Agentic ChatService powered by LangGraph.
    It orchestrates RAG and deterministic tools through a state machine.
    """

    def __init__(
        self,
        conversation_repo: ConversationRepoProto,
        graph: Runnable,
        history_limit: int = 5,
    ):
        # We pass None for rewriter/citations because the Graph internalizes them
        super().__init__(conversation_repo, None, None, history_limit)  # type: ignore
        self._graph = graph

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Executes the agentic graph to fulfill the chat request.
        """
        # Resolve conversation state
        conversation = await self._resolve_conversation(request)
        history = await self._conversation_repo.get_recent_messages(
            conversation.id, limit=self._history_limit
        )

        # Initialize graph state
        initial_state: AgentGraphState = {
            "conversation_id": conversation.id,
            "original_question": request.question,
            "rewritten_question": "",
            "scope": request.scope,
            "history": history,
            "current_strategy": None,
            "tool_calls": [],
            "retrieved_context": None,
            "tool_context": None,
            "citations": [],
            "answer": None,
            "reasoning_trace": [],
            "step_count": 0,
            "done": False,
        }

        logger.info(
            "graph_chat.start conversation_id=%s scope_type=%s repository_id=%s document_id=%s question=%r",
            conversation.id,
            request.scope.type,
            request.scope.repository_id,
            request.scope.document_id,
            request.question,
        )

        result = await self._graph.ainvoke(initial_state)

        answer = result.get("answer", "I'm sorry, I couldn't process your request.")
        citations = result.get("citations", [])
        rewritten = result.get("rewritten_question")

        logger.info(
            "graph_chat.end conversation_id=%s strategy=%s step_count=%s citations=%s answer_preview=%r reasoning_trace=%s",
            conversation.id,
            result.get("current_strategy"),
            result.get("step_count"),
            len(citations),
            answer[:200],
            result.get("reasoning_trace", []),
        )

        rewritten_to_save = rewritten if rewritten != request.question else None

        await self._persist_turn(
            conversation_id=conversation.id,
            user_question=request.question,
            rewritten_question=rewritten_to_save,
            answer=answer,
            citations=citations,
        )

        return ChatResponse(
            conversation_id=conversation.id, answer=answer, citations=citations
        )
