from abc import ABC, abstractmethod


class LLMGeneratorProto(ABC):
    @abstractmethod
    async def generate_summary(self, text: str, context: str = "") -> str:
        pass
