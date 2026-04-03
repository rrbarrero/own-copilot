from typing import Protocol

from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.schemas.chat import ChatScope


class LexicalRetrievalProviderProto(Protocol):
    async def search(
        self,
        question: str,
        scope: ChatScope,
        top_k: int = 5,
    ) -> list[RetrievedChunk]: ...
