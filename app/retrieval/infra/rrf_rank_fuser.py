from app.retrieval.domain.retrieved_chunk import RetrievedChunk


class RRFRankFuser:
    def __init__(self, k: int = 60):
        self._k = k

    def fuse(
        self,
        vector_results: list[RetrievedChunk],
        lexical_results: list[RetrievedChunk],
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        # Reciprocal Rank Fusion (RRF) algorithm:
        # Each chunk is assigned a score based on its rank in each source.

        # We need a way to identify unique chunks
        def get_chunk_key(chunk: RetrievedChunk) -> str:
            return f"{chunk.document_uuid}:{chunk.chunk_index}"

        scores: dict[str, float] = {}
        chunks: dict[str, RetrievedChunk] = {}

        # Process vector results
        for rank, chunk in enumerate(vector_results, start=1):
            key = get_chunk_key(chunk)
            scores[key] = scores.get(key, 0.0) + (1.0 / (self._k + rank))
            chunks[key] = chunk

        # Process lexical results
        for rank, chunk in enumerate(lexical_results, start=1):
            key = get_chunk_key(chunk)
            scores[key] = scores.get(key, 0.0) + (1.0 / (self._k + rank))
            # If it's already there, keep the one with higher score from vector?
            # Or just keep the last one.
            # RRF uses the chunk info, but the score is replaced.
            if key not in chunks:
                chunks[key] = chunk

        # Sort by RRF score
        sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        final_results = []
        for key in sorted_keys[:top_k]:
            original_chunk = chunks[key]
            # Create a new RetrievedChunk with the merged RRF score
            # Note: We replace the original score with the RRF score
            fused_chunk = RetrievedChunk(
                document_uuid=original_chunk.document_uuid,
                chunk_index=original_chunk.chunk_index,
                content=original_chunk.content,
                path=original_chunk.path,
                filename=original_chunk.filename,
                source_type=original_chunk.source_type,
                repository_id=original_chunk.repository_id,
                score=scores[key],
                metadata=original_chunk.metadata,
            )
            final_results.append(fused_chunk)

        return final_results
