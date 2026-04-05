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
        is_abstract = self._is_abstract_question(question)
        provider_top_k = top_k * 3 if is_abstract else top_k * 2

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
            top_k=provider_top_k,
            threshold=threshold,
        )

        # 2. Lexical Search
        lexical_results = await self._lexical_provider.search(
            question=question,
            scope=scope,
            top_k=provider_top_k,
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
        results = self._rank_fuser.fuse(
            vector_results=vector_results,
            lexical_results=lexical_results,
            top_k=provider_top_k,
        )

        if not is_abstract:
            return results[:top_k]

        return self._rebalance_abstract_results(results, top_k=top_k)

    @staticmethod
    def _is_abstract_question(question: str | None) -> bool:
        if not question:
            return False

        lowered = question.lower()
        return any(
            term in lowered
            for term in [
                "responsibility",
                "purpose",
                "role",
                "overview",
                "summary",
                "high level",
                "architecture",
                "what does",
                "doing",
                "intent",
                "goal",
            ]
        )

    def _rebalance_abstract_results(
        self, results: list[RetrievedChunk], top_k: int
    ) -> list[RetrievedChunk]:
        summaries = [r for r in results if r.metadata.get("chunk_kind") == "summary"]
        if not summaries:
            return results[:top_k]

        summary_cap = min(len(summaries), max(1, top_k // 2))
        selected_keys: set[tuple[object, int]] = set()
        selected: list[RetrievedChunk] = []

        for chunk in summaries[:summary_cap]:
            key = (chunk.document_uuid, chunk.chunk_index)
            selected_keys.add(key)
            selected.append(chunk)

        for chunk in results:
            key = (chunk.document_uuid, chunk.chunk_index)
            if key in selected_keys:
                continue
            selected.append(chunk)
            selected_keys.add(key)
            if len(selected) >= top_k:
                break

        logger.info(
            "hybrid_retrieval.raptor_bias "
            "abstract_query summaries_selected=%d top_k=%d",
            min(len(summaries), summary_cap),
            top_k,
        )
        return selected[:top_k]
