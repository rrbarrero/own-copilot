from app.config import settings
from app.factory import (
    create_chunk_repo,
    create_document_repo,
    create_storage_repo,
)
from app.worker.application.pipeline import Pipeline
from app.worker.application.steps.chunking_step import ChunkingStep
from app.worker.application.steps.generate_embeddings_step import (
    GenerateEmbeddingsStep,
)
from app.worker.application.steps.load_document import LoadDocumentStep
from app.worker.application.steps.save_chunks_step import SaveChunksStep
from app.worker.domain.step_proto import StepProto
from app.worker.infrastructure.chunkers.recursive_character_chunker import (
    RecursiveCharacterChunker,
)
from app.worker.infrastructure.embeddings.ollama_embedding_service import (
    OllamaEmbeddingService,
)


def create_pipeline() -> Pipeline:
    # 1. Initialize repositories
    doc_repo = create_document_repo()
    chunk_repo = create_chunk_repo()
    storage_repo = create_storage_repo()

    # 2. Initialize domain services
    chunker = RecursiveCharacterChunker(chunk_size=1000, chunk_overlap=200)
    embedding_service = OllamaEmbeddingService(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )

    # 3. Assemble steps in logical order
    steps: list[StepProto] = [
        LoadDocumentStep(document_repo=doc_repo, storage_repo=storage_repo),
        ChunkingStep(chunker=chunker),
        GenerateEmbeddingsStep(embedding_service=embedding_service),
        SaveChunksStep(chunk_repo=chunk_repo),
    ]

    # 4. Create and return the pipeline orchestrator
    return Pipeline(steps=steps)
