from typing import Protocol
from uuid import UUID

from app.conversation.domain.conversation import Conversation
from app.conversation.domain.conversation_message import ConversationMessage


class ConversationRepoProto(Protocol):
    async def get_by_id(self, conversation_id: UUID) -> Conversation | None: ...
    async def create(self, conversation: Conversation) -> None: ...
    async def add_message(self, message: ConversationMessage) -> None: ...
    async def get_recent_messages(
        self, conversation_id: UUID, limit: int = 8
    ) -> list[ConversationMessage]: ...
