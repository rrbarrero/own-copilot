from uuid import UUID

from langchain_ollama import ChatOllama

from app.prompts.rag_prompt import RAG_PROMPT_TEMPLATE
from app.retrieval.application.context_builder import ContextBuilder
from app.retrieval.application.retriever import Retriever
from app.schemas.chat import ChatRequest, ChatResponse

# Sentinel UUID used by ChatWithCitations: ChatService always overwrites this
# with the real conversation_id before returning to the caller.
_NO_CONVERSATION_ID = UUID(int=0)


class ChatWithCitations:
    def __init__(
        self,
        retriever: Retriever,
        llm: ChatOllama,
        context_builder: ContextBuilder | None = None,
    ):
        self._retriever = retriever
        self._llm = llm
        self._context_builder = context_builder or ContextBuilder()

    async def chat(self, request: ChatRequest) -> ChatResponse:
        # 1. Retrieve relevant chunks
        chunks = await self._retriever.retrieve(
            question=request.question,
            scope=request.scope,
        )

        # 2. Build context and citations
        context_str, citations = self._context_builder.build_context(chunks)

        # 3. If no context was found, we handle it as per the prompt instructions.
        # But we still call the LLM with empty context if needed, however the
        # prompt and our prompt template instructions should yield a proper refusal.
        prompt_str = RAG_PROMPT_TEMPLATE.format(
            context=context_str if context_str else "NOTHING FOUND.",
            question=request.question,
        )

        # 4. Invoke LLM
        response = await self._llm.ainvoke(prompt_str)

        # response.content might be Union[list[dict | str], str] according to type hint
        # but for ChatOllama it's usually str or a list of message contents.
        # langchain models usually return str in .content for non-multimodal models.
        answer = str(response.content)

        return ChatResponse(
            conversation_id=_NO_CONVERSATION_ID,
            answer=answer,
            citations=citations,
        )
