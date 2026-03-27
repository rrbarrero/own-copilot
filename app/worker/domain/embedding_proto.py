from typing import Protocol


class EmbeddingProto(Protocol):
    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
