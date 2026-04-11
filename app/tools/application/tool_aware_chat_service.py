from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage

from app.conversation.application.chat_service import ChatService
from app.conversation.application.question_rewriter import QuestionRewriter
from app.conversation.domain.conversation_repo_proto import ConversationRepoProto
from app.retrieval.application.chat_with_citations import ChatWithCitations
from app.schemas.chat import ChatRequest, ChatResponse, ScopeType
from app.tools.application.repository_tool_service import RepositoryToolService
from app.tools.application.tool_picker import ToolPicker


class ToolAwareChatService(ChatService):
    def __init__(
        self,
        conversation_repo: ConversationRepoProto,
        question_rewriter: QuestionRewriter,
        chat_with_citations: ChatWithCitations,
        tool_service: RepositoryToolService,
        llm: BaseChatModel,
        history_limit: int = 8,
    ):
        super().__init__(
            conversation_repo=conversation_repo,
            question_rewriter=question_rewriter,
            chat_with_citations=chat_with_citations,
            history_limit=history_limit,
        )
        self._tool_service = tool_service
        self._llm = llm
        self._tool_picker = ToolPicker(llm)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        conversation = await self._resolve_conversation(request)
        resolved_request = request.model_copy(
            update={"conversation_id": conversation.id}
        )
        history = await self._conversation_repo.get_recent_messages(
            conversation.id, limit=self._history_limit
        )

        standalone_q = await self._question_rewriter.rewrite(
            question=request.question,
            history=history,
        )

        if request.scope.type != ScopeType.REPOSITORY:
            return await super().chat(resolved_request)

        if not request.scope.repository_id:
            return await super().chat(resolved_request)

        decision = await self._tool_picker.decide(standalone_q)
        repo_id = request.scope.repository_id

        if decision.strategy == "rag":
            return await super().chat(resolved_request)

        tool_output = ""
        try:
            if decision.strategy == "find_files":
                files = await self._tool_service.find_files(
                    repository_id=repo_id,
                    repository_sync_id=request.scope.repository_sync_id,
                    **decision.parameters,
                )
                items = [f"- {f.path} ({f.size_bytes} bytes)" for f in files]
                tool_output = "\n".join(items) or "No files found."

            elif decision.strategy == "read_file":
                read_res = await self._tool_service.read_file(
                    repository_id=repo_id,
                    repository_sync_id=request.scope.repository_sync_id,
                    **decision.parameters,
                )
                tool_output = f"Content of {read_res.path}:\n\n{read_res.content}"
                if read_res.truncated:
                    tool_output += "\n\n[CONTENT TRUNCATED]"

            elif decision.strategy == "search_in_repo":
                matches = await self._tool_service.search_in_repo(
                    repository_id=repo_id,
                    repository_sync_id=request.scope.repository_sync_id,
                    **decision.parameters,
                )
                items = [f"{m.path}:{m.line_number}: {m.line_content}" for m in matches]
                tool_output = "\n".join(items) or "No results found."
            else:
                return await super().chat(resolved_request)
        except Exception:
            return await super().chat(resolved_request)

        prompt = (
            "You are a technical assistant. Answer the user question EXCLUSIVELY "
            "based on the following deterministic tool output.\n\n"
            "RULES:\n"
            "1. If the context is empty or does not contain the answer, say: "
            "\"I'm sorry, I don't have enough information to answer that.\"\n"
            "2. Do NOT use external knowledge.\n"
            "3. Answer in the same language as the question.\n\n"
            f"CONTEXT:\n{tool_output}\n\n"
            f"QUESTION: {request.question}\n\n"
            "ANSWER:"
        )
        messages = [SystemMessage(content=prompt)]
        ans_res = await self._llm.ainvoke(messages)
        answer = str(ans_res.content)

        rewritten = standalone_q if standalone_q != request.question else None
        await self._persist_turn(
            conversation_id=conversation.id,
            user_question=request.question,
            rewritten_question=rewritten,
            answer=answer,
            citations=None,
        )

        return ChatResponse(
            answer=answer,
            conversation_id=conversation.id,
            citations=[],
        )
