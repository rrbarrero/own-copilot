from typing import cast
from uuid import UUID, uuid4

import pytest

from app.retrieval.domain.hybrid_rank_fuser_proto import HybridRankFuserProto
from app.retrieval.domain.lexical_retrieval_provider_proto import (
    LexicalRetrievalProviderProto,
)
from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.retrieval.domain.vector_retrieval_provider_proto import (
    VectorRetrievalProviderProto,
)
from app.retrieval.infra.hybrid_retrieval_service import HybridRetrievalService
from app.schemas.chat import ChatScope, ScopeType


class StubVectorProvider:
    def __init__(self, results: list[RetrievedChunk]):
        self.results = results
        self.calls: list[dict[str, float | int]] = []

    async def search(
        self,
        query_embedding: list[float],  # noqa: ARG002
        scope: ChatScope,  # noqa: ARG002
        top_k: int,
        threshold: float,
    ) -> list[RetrievedChunk]:
        self.calls.append({"top_k": top_k, "threshold": threshold})
        return self.results


class StubLexicalProvider:
    def __init__(self, results: list[RetrievedChunk]):
        self.results = results
        self.calls: list[dict[str, str | int]] = []

    async def search(
        self,
        question: str,
        scope: ChatScope,  # noqa: ARG002
        top_k: int,
    ) -> list[RetrievedChunk]:
        self.calls.append({"top_k": top_k, "question": question})
        return self.results


class StubRankFuser:
    def __init__(self, fused_results: list[RetrievedChunk]):
        self.fused_results = fused_results
        self.calls: list[dict[str, int]] = []

    def fuse(
        self,
        vector_results: list[RetrievedChunk],  # noqa: ARG002
        lexical_results: list[RetrievedChunk],  # noqa: ARG002
        top_k: int,
    ) -> list[RetrievedChunk]:
        self.calls.append({"top_k": top_k})
        return self.fused_results[:top_k]


def _chunk(*, chunk_index: int, kind: str) -> RetrievedChunk:
    return RetrievedChunk(
        document_uuid=uuid4(),
        chunk_index=chunk_index,
        content=f"{kind}-{chunk_index}",
        path="src/sample.py",
        filename="sample.py",
        source_type="repository",
        repository_id=cast(UUID, uuid4()),
        score=1.0,
        metadata={"chunk_kind": kind},
    )


@pytest.mark.asyncio
async def test_hybrid_retrieval_service_limits_summary_bias_for_abstract_queries():
    fused_results = [
        _chunk(chunk_index=10, kind="summary"),
        _chunk(chunk_index=0, kind="raw"),
        _chunk(chunk_index=1, kind="raw"),
        _chunk(chunk_index=11, kind="summary"),
        _chunk(chunk_index=2, kind="raw"),
        _chunk(chunk_index=12, kind="summary"),
    ]
    vector_provider = StubVectorProvider(fused_results)
    lexical_provider = StubLexicalProvider(fused_results)
    rank_fuser = StubRankFuser(fused_results)
    service = HybridRetrievalService(
        vector_provider=cast(VectorRetrievalProviderProto, vector_provider),
        lexical_provider=cast(LexicalRetrievalProviderProto, lexical_provider),
        rank_fuser=cast(HybridRankFuserProto, rank_fuser),
    )

    results = await service.search(
        query_embedding=[0.1, 0.2],
        scope=ChatScope(type=ScopeType.REPOSITORY, repository_id=uuid4()),
        top_k=4,
        threshold=0.5,
        question="Give me a high level overview of the architecture",
    )

    assert [chunk.metadata["chunk_kind"] for chunk in results] == [
        "summary",
        "summary",
        "raw",
        "raw",
    ]
    assert rank_fuser.calls[0]["top_k"] == 12
    assert vector_provider.calls[0]["top_k"] == 12
    assert lexical_provider.calls[0]["top_k"] == 12


@pytest.mark.asyncio
async def test_hybrid_retrieval_service_keeps_ranked_order_for_non_abstract_queries():
    fused_results = [
        _chunk(chunk_index=0, kind="raw"),
        _chunk(chunk_index=10, kind="summary"),
        _chunk(chunk_index=1, kind="raw"),
    ]
    service = HybridRetrievalService(
        vector_provider=cast(
            VectorRetrievalProviderProto, StubVectorProvider(fused_results)
        ),
        lexical_provider=cast(
            LexicalRetrievalProviderProto, StubLexicalProvider(fused_results)
        ),
        rank_fuser=cast(HybridRankFuserProto, StubRankFuser(fused_results)),
    )

    results = await service.search(
        query_embedding=[0.1, 0.2],
        scope=ChatScope(type=ScopeType.REPOSITORY, repository_id=uuid4()),
        top_k=2,
        threshold=0.5,
        question="Where is the database pool configured?",
    )

    assert [chunk.chunk_index for chunk in results] == [0, 10]
