from langchain_ollama import OllamaEmbeddings


class OllamaQueryEmbeddingService:
    def __init__(self, model: str, base_url: str):
        self._embeddings = OllamaEmbeddings(
            model=model,
            base_url=base_url,
        )

    async def get_embedding(self, text: str) -> list[float]:
        # OllamaEmbeddings.aembed_query returns a list of floats
        return await self._embeddings.aembed_query(text)
