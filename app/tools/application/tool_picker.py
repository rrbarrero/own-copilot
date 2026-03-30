import json
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage


class ToolDecision:
    def __init__(
        self,
        strategy: Literal["rag", "find_files", "read_file", "search_in_repo"],
        parameters: dict,
        reasoning: str,
    ):
        self.strategy = strategy
        self.parameters = parameters
        self.reasoning = reasoning


class ToolPicker:
    _ALLOWED_STRATEGIES = {"rag", "find_files", "read_file", "search_in_repo"}

    def __init__(self, llm: BaseChatModel):
        self._llm = llm

    async def decide(self, question: str) -> ToolDecision:
        system_prompt = (
            "You are an assistant that decides the best tool to answer "
            "a question about a code repository.\n"
            "Options:\n"
            "- 'rag': for conceptual or general questions.\n"
            "- 'find_files': search files by name or path.\n"
            "- 'read_file': read content from ONE specific file.\n"
            "- 'search_in_repo': search for exact symbols or text.\n\n"
            "Respond ONLY with JSON: "
            '{"strategy": "...", "parameters": {...}, "reasoning": "..."}\n'
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Question: {question}"),
        ]

        response = await self._llm.ainvoke(messages)
        content = str(response.content)

        # Clean JSON if LLM wraps it in markdown
        if "```json" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
        elif "```" in content:
            # Handle cases with just triple backticks and no language tag
            parts = content.split("```")
            content = parts[1].strip() if len(parts) >= 3 else content.strip()

        try:
            data = json.loads(content)
            strategy = data.get("strategy", "rag")
            if strategy not in self._ALLOWED_STRATEGIES:
                return ToolDecision(
                    strategy="rag",
                    parameters={},
                    reasoning=f"Unsupported strategy: {strategy}",
                )

            return ToolDecision(
                strategy=strategy,
                parameters=data.get("parameters", {}),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, KeyError):
            return ToolDecision(
                strategy="rag",
                parameters={},
                reasoning="Fallback due to parsing error",
            )
