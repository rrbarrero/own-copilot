class InMemoryEmbeddingService:
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # For testing, return a dummy vector with a fixed size 1024
        # (matching the migration's vector(1024))
        return [[0.1] * 1024 for _ in texts]
