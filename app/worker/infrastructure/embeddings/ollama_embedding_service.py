# app/worker/infrastructure/embeddings/ollama_embedding_service.py
from langchain_ollama import OllamaEmbeddings


class OllamaEmbeddingService:
    def __init__(self, model: str, base_url: str):
        self._embeddings = OllamaEmbeddings(
            model=model,
            base_url=base_url,
        )

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embeddings.aembed_documents(texts)

    async def get_dimension(self) -> int:
        test_embed = await self.embed_documents(["test"])
        return len(test_embed[0])
