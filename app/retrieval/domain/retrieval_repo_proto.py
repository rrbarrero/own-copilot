from typing import Protocol

from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.schemas.chat import ChatScope


class RetrievalRepoProto(Protocol):
    async def search(
        self,
        query_embedding: list[float],
        scope: ChatScope,
        top_k: int = 5,
    ) -> list[RetrievedChunk]: ...
