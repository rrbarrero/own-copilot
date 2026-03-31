from typing import TypedDict
from uuid import UUID

from app.conversation.domain.conversation_message import ConversationMessage
from app.schemas.chat import ChatScope


class AgentGraphState(TypedDict):
    """
    State for the LangGraph agentic flow.
    """

    conversation_id: UUID
    original_question: str
    rewritten_question: str
    scope: ChatScope
    history: list[ConversationMessage]

    # Execution context
    current_strategy: str | None
    tool_calls: list[dict]
    retrieved_context: str | None
    tool_context: str | None
    citations: list[dict]

    # Result
    answer: str | None
    reasoning_trace: list[str]
    step_count: int
    done: bool
