from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.conversation.application.question_rewriter import QuestionRewriter
from app.conversation.domain.conversation import Conversation
from app.conversation.domain.conversation_message import ConversationMessage
from app.conversation.domain.conversation_repo_proto import ConversationRepoProto
from app.retrieval.application.chat_with_citations import ChatWithCitations
from app.schemas.chat import ChatRequest, ChatResponse, ScopeType


class ChatService:
    def __init__(
        self,
        conversation_repo: ConversationRepoProto,
        question_rewriter: QuestionRewriter,
        chat_with_citations: ChatWithCitations,
        history_limit: int = 8,
    ):
        self._conversation_repo = conversation_repo
        self._question_rewriter = question_rewriter
        self._chat_with_citations = chat_with_citations
        self._history_limit = history_limit

    async def chat(self, request: ChatRequest) -> ChatResponse:
        # 1. Resolve conversation
        conversation = await self._resolve_conversation(request)

        # 2. Load history
        history = await self._conversation_repo.get_recent_messages(
            conversation.id, limit=self._history_limit
        )

        # 3. Reformulate
        standalone_q = await self._question_rewriter.rewrite(
            question=request.question,
            history=history,
        )

        # 4. Execute RAG with the standalone question (new request — do not mutate)
        original_question = request.question
        rag_request = ChatRequest(question=standalone_q, scope=request.scope)
        response = await self._chat_with_citations.chat(rag_request)

        # 5. Persist turn
        rewritten = standalone_q if standalone_q != original_question else None
        citations = None
        if response.citations:
            citations = [cite.model_dump() for cite in response.citations]

        await self._persist_turn(
            conversation_id=conversation.id,
            user_question=original_question,
            rewritten_question=rewritten,
            answer=response.answer,
            citations=citations,
        )

        # 6. Ensure response includes conversation_id
        response.conversation_id = conversation.id
        return response

    async def _resolve_conversation(self, request: ChatRequest) -> Conversation:
        if request.conversation_id:
            conv = await self._conversation_repo.get_by_id(request.conversation_id)
            if conv:
                # Validate scope coherence
                self._validate_scope(conv, request)
                return conv

            # Create with provided UUID
            return await self._create_conversation(request, request.conversation_id)

        # Create a brand new conversation
        return await self._create_conversation(request)

    def _validate_scope(self, conversation: Conversation, request: ChatRequest):
        if str(conversation.scope_type) != str(request.scope.type):
            raise HTTPException(
                status_code=409, detail="Scope type mismatch for this conversation"
            )

        if conversation.scope_type == ScopeType.REPOSITORY and str(
            conversation.repository_id
        ) != str(request.scope.repository_id):
            raise HTTPException(
                status_code=409,
                detail="Repository ID mismatch for this conversation",
            )
        if conversation.scope_type == ScopeType.DOCUMENT and str(
            conversation.document_id
        ) != str(request.scope.document_id):
            raise HTTPException(
                status_code=409,
                detail="Document ID mismatch for this conversation",
            )

    async def _create_conversation(
        self, request: ChatRequest, conversation_id: UUID | None = None
    ) -> Conversation:
        now = datetime.now(UTC)
        conversation = Conversation(
            id=conversation_id or uuid4(),
            scope_type=request.scope.type,
            repository_id=request.scope.repository_id,
            document_id=request.scope.document_id,
            created_at=now,
            updated_at=now,
        )
        await self._conversation_repo.create(conversation)
        return conversation

    async def _persist_turn(
        self,
        conversation_id: UUID,
        user_question: str,
        rewritten_question: str | None,
        answer: str,
        citations: list[dict] | None,
    ):
        # 1. User message
        user_msg = ConversationMessage(
            id=uuid4(),
            conversation_id=conversation_id,
            role="user",
            content=user_question,
            rewritten_question=rewritten_question,
        )
        await self._conversation_repo.add_message(user_msg)

        # 2. Assistant message
        assistant_msg = ConversationMessage(
            id=uuid4(),
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            citations_json=citations,
        )
        await self._conversation_repo.add_message(assistant_msg)
