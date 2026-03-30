from langchain_ollama import ChatOllama

from app.conversation.domain.conversation_message import ConversationMessage
from app.prompts.rewrite_prompt import REWRITE_PROMPT_TEMPLATE


class QuestionRewriter:
    def __init__(self, llm: ChatOllama):
        self._llm = llm

    async def rewrite(
        self,
        question: str,
        history: list[ConversationMessage],
    ) -> str:
        if not history:
            return question

        history_str = self._format_history(history)
        prompt = REWRITE_PROMPT_TEMPLATE.format(
            history=history_str,
            question=question,
        )
        response = await self._llm.ainvoke(prompt)
        return str(response.content).strip()

    def _format_history(self, history: list[ConversationMessage]) -> str:
        lines = []
        for msg in history:
            role = "User" if msg.role == "user" else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)
