from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.ingestion.domain.document import (
    Document,
    DocumentType,
    ProcessingStatus,
    SourceType,
)
from app.ingestion.infra.in_memory_document_repo import InMemoryDocumentRepo
from app.ingestion.infra.in_memory_storage_repo import InMemoryStorageRepo
from app.worker.application.pipeline import Pipeline
from app.worker.application.steps.chunking_step import ChunkingStep
from app.worker.application.steps.generate_embeddings_step import GenerateEmbeddingsStep
from app.worker.application.steps.load_document import LoadDocumentStep
from app.worker.application.steps.save_chunks_step import SaveChunksStep
from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.step_proto import StepProto
from app.worker.infrastructure.chunkers.recursive_character_chunker import (
    RecursiveCharacterChunker,
)
from app.worker.infrastructure.embeddings.in_memory_embedding_service import (
    InMemoryEmbeddingService,
)


@pytest.mark.asyncio
async def test_full_pipeline_success():
    # 1. Setup in-memory dependencies
    doc_repo = InMemoryDocumentRepo()
    storage_repo = InMemoryStorageRepo()
    embedding_service = InMemoryEmbeddingService()

    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=10)

    # 2. Seed data
    doc_id = uuid4()
    doc_path = "test/doc.txt"
    content = (
        b"This is a long document that should be chunked into multiple pieces "
        b"for testing the pipeline."
    )

    doc = Document(
        uuid=doc_id,
        source_type=SourceType.UPLOAD,
        source_id="test-user",
        path=doc_path,
        filename="doc.txt",
        extension="txt",
        doc_type=DocumentType.TEXT,
        processing_status=ProcessingStatus.PENDING,
        size_bytes=len(content),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(doc)
    storage_repo.save(doc_path, content)

    # 3. Assemble Pipeline
    steps: list[StepProto] = [
        LoadDocumentStep(doc_repo, storage_repo),
        ChunkingStep(chunker),
        GenerateEmbeddingsStep(embedding_service),
        SaveChunksStep(doc_repo),
    ]
    pipeline = Pipeline(steps)

    # 4. Prepare Context
    ctx = PipelineContext(
        job_id="job-123", job_type="ingestion", payload={"document_id": str(doc_id)}
    )

    # 5. Run
    await pipeline.run(ctx)

    # 6. Assertions
    # Check context results
    assert ctx.original_bytes == content
    assert len(ctx.chunks) > 1
    assert "embedding" in ctx.chunks[0]
    assert len(ctx.chunks[0]["embedding"]) == 1024

    # Check persistence in in-memory repo
    saved_chunks = doc_repo.get_chunks(str(doc_id))
    assert len(saved_chunks) == len(ctx.chunks)
    assert saved_chunks[0]["content"] == ctx.chunks[0]["content"]
    assert saved_chunks[0]["embedding"] == ctx.chunks[0]["embedding"]
