from app.worker.domain.embedding_proto import EmbeddingProto
from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.step_proto import StepProto


class GenerateEmbeddingsStep(StepProto):
    def __init__(self, embedding_service: EmbeddingProto):
        self.embedding_service = embedding_service

    async def run(self, ctx: PipelineContext):
        # 1. Check if chunks are present (should be created by ChunkingStep)
        if not ctx.chunks:
            return  # No chunks, nothing to embed (or maybe raise error)

        # 2. Extract contents from chunks
        chunk_texts = [chunk["content"] for chunk in ctx.chunks]

        # 3. Generate embeddings
        # Batch processing is efficient
        embeddings = await self.embedding_service.embed_documents(chunk_texts)

        # 4. Attach embeddings back to chunk dictionaries
        for i, embedding in enumerate(embeddings):
            ctx.chunks[i]["embedding"] = embedding
