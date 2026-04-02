from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.ingestion.domain.document import (
    Document,
    DocumentStatus,
    DocumentType,
    SourceType,
)
from app.ingestion.infra.in_memory_chunk_repo import InMemoryChunkRepo
from app.ingestion.infra.in_memory_document_repo import InMemoryDocumentRepo
from app.ingestion.infra.in_memory_storage_repo import InMemoryStorageRepo
from app.worker.application.pipeline import Pipeline
from app.worker.application.steps.chunking_step import ChunkingStep
from app.worker.application.steps.generate_embeddings_step import GenerateEmbeddingsStep
from app.worker.application.steps.load_document import LoadDocumentStep
from app.worker.application.steps.normalize_document_step import NormalizeDocumentStep
from app.worker.application.steps.save_chunks_step import SaveChunksStep
from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.step_proto import StepProto
from app.worker.infrastructure.chunkers.chunking_strategy_selector import (
    ChunkingStrategySelector,
)
from app.worker.infrastructure.chunkers.document_aware_chunker import (
    DocumentAwareChunker,
)
from app.worker.infrastructure.embeddings.in_memory_embedding_service import (
    InMemoryEmbeddingService,
)


class FakePdfNormalizer:
    def supports(self, context):  # noqa: ANN001
        return context.extension == "pdf"

    def normalize(self, content: bytes, context):  # noqa: ARG002, ANN001
        return {
            "text": "# PDF Title\n\n## Section\n\nNormalized markdown from pdf.",
            "format": "markdown",
            "metadata": {"source_format": "pdf", "page_count": 1},
        }


@pytest.mark.asyncio
async def test_full_pipeline_success():
    # 1. Setup in-memory dependencies
    doc_repo = InMemoryDocumentRepo()
    chunk_repo = InMemoryChunkRepo()
    storage_repo = InMemoryStorageRepo()
    embedding_service = InMemoryEmbeddingService()

    selector = ChunkingStrategySelector(chunk_size=50, chunk_overlap=10)
    chunker = DocumentAwareChunker(selector=selector)

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
        processing_status=DocumentStatus.QUEUED,
        size_bytes=len(content),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(doc)
    await storage_repo.save(doc_path, content)

    # 3. Assemble Pipeline
    steps: list[StepProto] = [
        LoadDocumentStep(doc_repo, storage_repo),
        NormalizeDocumentStep(normalizers=[]),
        ChunkingStep(chunker),
        GenerateEmbeddingsStep(embedding_service),
        SaveChunksStep(chunk_repo),
    ]
    pipeline = Pipeline(steps)

    # 4. Prepare Context
    ctx = PipelineContext(
        job_id="job-123",
        job_type="ingestion",
        payload={"doc_uuid": str(doc_id)},
        document_id=str(doc_id),
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
    saved_chunks = chunk_repo.get_chunks(str(doc_id))
    assert len(saved_chunks) == len(ctx.chunks)
    assert saved_chunks[0]["content"] == ctx.chunks[0]["content"]
    assert saved_chunks[0]["embedding"] == ctx.chunks[0]["embedding"]


@pytest.mark.asyncio
async def test_full_pipeline_uses_specialized_markdown_strategy():
    doc_repo = InMemoryDocumentRepo()
    chunk_repo = InMemoryChunkRepo()
    storage_repo = InMemoryStorageRepo()
    embedding_service = InMemoryEmbeddingService()

    selector = ChunkingStrategySelector(chunk_size=40, chunk_overlap=0)
    chunker = DocumentAwareChunker(selector=selector)

    doc_id = uuid4()
    doc_path = "test/readme.md"
    content = (
        b"# Title\n\n"
        b"Intro paragraph for the document.\n\n"
        b"## Section\n\n"
        b"Some more markdown content here."
    )

    doc = Document(
        uuid=doc_id,
        source_type=SourceType.UPLOAD,
        source_id="test-user",
        path=doc_path,
        filename="readme.md",
        extension="md",
        doc_type=DocumentType.MARKDOWN,
        processing_status=DocumentStatus.QUEUED,
        size_bytes=len(content),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await doc_repo.save(doc)
    await storage_repo.save(doc_path, content)

    steps: list[StepProto] = [
        LoadDocumentStep(doc_repo, storage_repo),
        NormalizeDocumentStep(normalizers=[]),
        ChunkingStep(chunker),
        GenerateEmbeddingsStep(embedding_service),
        SaveChunksStep(chunk_repo),
    ]
    pipeline = Pipeline(steps)

    ctx = PipelineContext(
        job_id="job-md-123",
        job_type="ingestion",
        payload={"doc_uuid": str(doc_id)},
        document_id=str(doc_id),
    )

    await pipeline.run(ctx)

    assert ctx.filename == "readme.md"
    assert ctx.extension == "md"
    assert ctx.doc_type == DocumentType.MARKDOWN.value
    assert len(ctx.chunks) >= 2
    assert any("Title" in chunk["content"] for chunk in ctx.chunks)

    saved_chunks = chunk_repo.get_chunks(str(doc_id))
    assert len(saved_chunks) == len(ctx.chunks)


@pytest.mark.asyncio
async def test_full_pipeline_normalizes_pdf_before_chunking():
    doc_repo = InMemoryDocumentRepo()
    chunk_repo = InMemoryChunkRepo()
    storage_repo = InMemoryStorageRepo()
    embedding_service = InMemoryEmbeddingService()

    selector = ChunkingStrategySelector(chunk_size=40, chunk_overlap=0)
    chunker = DocumentAwareChunker(selector=selector)

    doc_id = uuid4()
    doc_path = "test/paper.pdf"
    content = b"%PDF-1.7 fake pdf content"

    doc = Document(
        uuid=doc_id,
        source_type=SourceType.UPLOAD,
        source_id="test-user",
        path=doc_path,
        filename="paper.pdf",
        extension="pdf",
        doc_type=DocumentType.PDF,
        processing_status=DocumentStatus.QUEUED,
        size_bytes=len(content),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        mime_type="application/pdf",
    )
    await doc_repo.save(doc)
    await storage_repo.save(doc_path, content)

    steps: list[StepProto] = [
        LoadDocumentStep(doc_repo, storage_repo),
        NormalizeDocumentStep(normalizers=[FakePdfNormalizer()]),
        ChunkingStep(chunker),
        GenerateEmbeddingsStep(embedding_service),
        SaveChunksStep(chunk_repo),
    ]
    pipeline = Pipeline(steps)

    ctx = PipelineContext(
        job_id="job-pdf-123",
        job_type="ingestion",
        payload={"doc_uuid": str(doc_id)},
        document_id=str(doc_id),
    )

    await pipeline.run(ctx)

    assert ctx.mime_type == "application/pdf"
    assert ctx.normalized_document is not None
    assert ctx.normalized_document["format"] == "markdown"
    assert len(ctx.chunks) >= 1
    assert any("PDF Title" in chunk["content"] for chunk in ctx.chunks)
