from typing import Protocol


class QueryEmbeddingServiceProto(Protocol):
    async def get_embedding(self, text: str) -> list[float]: ...
