import uuid

from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.retrieval.infra.rrf_rank_fuser import RRFRankFuser


def create_chunk(doc_uuid, index, content, score):
    return RetrievedChunk(
        document_uuid=doc_uuid,
        chunk_index=index,
        content=content,
        path=f"path/{index}",
        filename=f"file_{index}.py",
        source_type="upload",
        repository_id=None,
        score=score,
        metadata={},
    )


def test_rrf_fusion_logic():
    fuser = RRFRankFuser(k=1)  # Using k=1 for easy math
    doc1 = uuid.uuid4()
    doc2 = uuid.uuid4()

    # Vector results: [A, B]
    # Lexical results: [B, C]
    # Expectations:
    # A has rank 1 in vector (1/(1+1)=0.5), 0 in lexical. Total=0.5
    # B has rank 2 in vector (1/(1+2)=0.33), rank 1 in lexical (1/(1+1)=0.5). Total=0.83
    # C has rank 0 in vector, rank 2 in lexical (1/(1+2)=0.33). Total=0.33

    # Winner should be B.

    chunk_a = create_chunk(doc1, 0, "Content A", 0.9)
    chunk_b = create_chunk(doc1, 1, "Content B", 0.8)
    chunk_c = create_chunk(doc2, 0, "Content C", 0.7)

    vector_results = [chunk_a, chunk_b]
    lexical_results = [chunk_b, chunk_c]

    fused = fuser.fuse(vector_results, lexical_results, top_k=3)

    assert len(fused) == 3
    assert fused[0].document_uuid == doc1
    assert fused[0].chunk_index == 1  # B won
    assert abs(fused[0].score - 0.8333333333333333) < 0.0001

    assert fused[1].document_uuid == doc1
    assert fused[1].chunk_index == 0  # A is second
    assert fused[1].score == 0.5

    assert fused[2].document_uuid == doc2
    assert fused[2].chunk_index == 0  # C is third
    assert abs(fused[2].score - 0.3333333333333333) < 0.0001
