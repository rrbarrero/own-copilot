from functools import lru_cache

from langchain_ollama import ChatOllama

from app.config import settings


@lru_cache
def get_llm(
    model: str = settings.LLM_MODEL, temperature: float = settings.LLM_TEMPERATURE
) -> ChatOllama:
    """
    Factory to get the LLM model.
    """
    return ChatOllama(
        model=model, temperature=temperature, base_url=settings.OLLAMA_BASE_URL
    )
