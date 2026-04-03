from typing import Protocol

from app.retrieval.domain.retrieved_chunk import RetrievedChunk


class HybridRankFuserProto(Protocol):
    def fuse(
        self,
        vector_results: list[RetrievedChunk],
        lexical_results: list[RetrievedChunk],
        top_k: int = 5,
    ) -> list[RetrievedChunk]: ...
