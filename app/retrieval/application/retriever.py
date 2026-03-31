import logging

from app.retrieval.domain.query_embedding_proto import QueryEmbeddingServiceProto
from app.retrieval.domain.retrieval_repo_proto import RetrievalRepoProto
from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.schemas.chat import ChatScope

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(
        self,
        retrieval_repo: RetrievalRepoProto,
        embedding_service: QueryEmbeddingServiceProto,
        top_k: int = 5,
        threshold: float = 0.5,
        fallback_threshold: float | None = None,
    ):
        self._retrieval_repo = retrieval_repo
        self._embedding_service = embedding_service
        self._top_k = top_k
        self._threshold = threshold
        self._fallback_threshold = fallback_threshold

    async def retrieve(
        self,
        question: str,
        scope: ChatScope,
    ) -> list[RetrievedChunk]:
        # Generate embedding for the question
        query_embedding = await self._embedding_service.get_embedding(question)

        results = await self._retrieval_repo.search(
            query_embedding=query_embedding,
            scope=scope,
            top_k=self._top_k,
            threshold=self._threshold,
        )

        if results or self._fallback_threshold is None:
            return results

        if self._fallback_threshold >= self._threshold:
            return results

        logger.info(
            "retriever.fallback_retry scope_type=%s repository_id=%s document_id=%s primary_threshold=%s fallback_threshold=%s question=%r",
            scope.type,
            scope.repository_id,
            scope.document_id,
            self._threshold,
            self._fallback_threshold,
            question,
        )

        return await self._retrieval_repo.search(
            query_embedding=query_embedding,
            scope=scope,
            top_k=self._top_k,
            threshold=self._fallback_threshold,
        )
