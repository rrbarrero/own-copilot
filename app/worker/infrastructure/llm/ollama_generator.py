from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.worker.domain.llm_generator_proto import LLMGeneratorProto


class OllamaGenerator(LLMGeneratorProto):
    def __init__(self, model: str, base_url: str, temperature: float = 0.0):
        self._llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
        )

    async def generate_summary(self, text: str, context: str = "") -> str:
        system_prompt = (
            "Eres un experto en análisis de código. "
            "Tu tarea es generar un resumen breve, factual y técnico "
            "del fragmento proporcionado. "
            "Enfócate en la responsabilidad, el propósito y los símbolos clave. "
            "No inventes información que no esté presente. "
            "Responde solo con el resumen, sin preámbulos."
        )

        user_prompt = f"Contenido a resumir:\n\n{text}"
        if context:
            user_prompt = f"Contexto (archivo/módulo):\n{context}\n\n{user_prompt}"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self._llm.ainvoke(messages)
        return str(response.content).strip()
