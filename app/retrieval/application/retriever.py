from app.retrieval.domain.query_embedding_proto import QueryEmbeddingServiceProto
from app.retrieval.domain.retrieval_repo_proto import RetrievalRepoProto
from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.schemas.chat import ChatScope


class Retriever:
    def __init__(
        self,
        retrieval_repo: RetrievalRepoProto,
        embedding_service: QueryEmbeddingServiceProto,
        top_k: int = 5,
        threshold: float = 0.5,
    ):
        self._retrieval_repo = retrieval_repo
        self._embedding_service = embedding_service
        self._top_k = top_k
        self._threshold = threshold

    async def retrieve(
        self,
        question: str,
        scope: ChatScope,
    ) -> list[RetrievedChunk]:
        # Generate embedding for the question
        query_embedding = await self._embedding_service.get_embedding(question)

        # Search the repository
        return await self._retrieval_repo.search(
            query_embedding=query_embedding,
            scope=scope,
            top_k=self._top_k,
            threshold=self._threshold,
        )
