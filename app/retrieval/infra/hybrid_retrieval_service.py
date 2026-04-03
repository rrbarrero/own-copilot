import logging

from app.retrieval.domain.hybrid_rank_fuser_proto import HybridRankFuserProto
from app.retrieval.domain.lexical_retrieval_provider_proto import (
    LexicalRetrievalProviderProto,
)
from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.retrieval.domain.vector_retrieval_provider_proto import (
    VectorRetrievalProviderProto,
)
from app.schemas.chat import ChatScope

logger = logging.getLogger(__name__)


class HybridRetrievalService:
    def __init__(
        self,
        vector_provider: VectorRetrievalProviderProto,
        lexical_provider: LexicalRetrievalProviderProto,
        rank_fuser: HybridRankFuserProto,
    ):
        self._vector_provider = vector_provider
        self._lexical_provider = lexical_provider
        self._rank_fuser = rank_fuser

    async def search(
        self,
        query_embedding: list[float],
        scope: ChatScope,
        top_k: int = 5,
        threshold: float = 0.5,
        question: str | None = None,
    ) -> list[RetrievedChunk]:
        # If no question is provided, fallback to vector only
        if not question:
            return await self._vector_provider.search(
                query_embedding=query_embedding,
                scope=scope,
                top_k=top_k,
                threshold=threshold,
            )

        # 1. Vector Search
        # We might search for more than top_k to have enough pool for fusion
        vector_results = await self._vector_provider.search(
            query_embedding=query_embedding,
            scope=scope,
            top_k=top_k * 2,  # Pool for fusion
            threshold=threshold,
        )

        # 2. Lexical Search
        lexical_results = await self._lexical_provider.search(
            question=question,
            scope=scope,
            top_k=top_k * 2,  # Pool for fusion
        )

        logger.info(
            "hybrid_retrieval.results vector_count=%d lexical_count=%d question=%r",
            len(vector_results),
            len(lexical_results),
            question,
        )

        if not lexical_results:
            return vector_results[:top_k]

        if not vector_results:
            # Preserve the original threshold semantics from vector retrieval:
            # lexical evidence can improve ranking, but it must not bypass the
            # vector gate that determines whether a retrieval attempt succeeded.
            return []

        # 3. Fuse rankings
        return self._rank_fuser.fuse(
            vector_results=vector_results,
            lexical_results=lexical_results,
            top_k=top_k,
        )
