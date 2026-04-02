from app.config import settings
from app.factory import (
    create_chunk_repo,
    create_document_repo,
    create_job_repo,
    create_repository_repo,
    create_repository_sync_repo,
    create_storage_repo,
)
from app.repositories.infra.repository_scanner import RepositoryScanner
from app.repositories.infra.subprocess_git_repository_service import (
    SubprocessGitRepositoryService,
)
from app.worker.application.document_processing_service import (
    DocumentProcessingService,
)
from app.worker.application.ingestion_worker import IngestionWorker
from app.worker.application.job_handler_proto import JobHandlerProto
from app.worker.application.job_handlers.process_document_handler import (
    ProcessDocumentJobHandler,
)
from app.worker.application.job_handlers.sync_repository_handler import (
    SyncRepositoryJobHandler,
)
from app.worker.application.pipeline import Pipeline
from app.worker.application.steps.chunking_step import ChunkingStep
from app.worker.application.steps.generate_embeddings_step import (
    GenerateEmbeddingsStep,
)
from app.worker.application.steps.load_document import LoadDocumentStep
from app.worker.application.steps.save_chunks_step import SaveChunksStep
from app.worker.domain.step_proto import StepProto
from app.worker.infrastructure.chunkers.chunking_strategy_selector import (
    ChunkingStrategySelector,
)
from app.worker.infrastructure.chunkers.document_aware_chunker import (
    DocumentAwareChunker,
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
    selector = ChunkingStrategySelector(chunk_size=1000, chunk_overlap=200)
    chunker = DocumentAwareChunker(selector=selector)
    embedding_service = OllamaEmbeddingService(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )

    # 3. Assemble steps in logical order (Pipeline Composition Root)
    steps: list[StepProto] = [
        LoadDocumentStep(document_repo=doc_repo, storage_repo=storage_repo),
        ChunkingStep(chunker=chunker),
        GenerateEmbeddingsStep(embedding_service=embedding_service),
        SaveChunksStep(chunk_repo=chunk_repo),
    ]

    # 4. Create and return the pipeline orchestrator
    return Pipeline(steps=steps)


def create_worker() -> IngestionWorker:
    """
    Factory to create a fully configured IngestionWorker.
    This acts as the Composition Root for the background worker.
    """
    doc_repo = create_document_repo()
    storage_repo = create_storage_repo()
    pipeline = create_pipeline()

    processing_service = DocumentProcessingService(doc_repo=doc_repo, pipeline=pipeline)

    # Register handlers
    handlers: dict[str, JobHandlerProto] = {
        "process_document": ProcessDocumentJobHandler(processing_service),
        "sync_repository": SyncRepositoryJobHandler(
            repository_repo=create_repository_repo(),
            sync_repo=create_repository_sync_repo(),
            git_service=SubprocessGitRepositoryService(
                checkouts_root=f"{settings.STORAGE_PATH}/checkouts"
            ),
            scanner=RepositoryScanner(),
            document_repo=doc_repo,
            storage_repo=storage_repo,
            processing_service=processing_service,
        ),
    }

    return IngestionWorker(
        job_repo=create_job_repo(),
        handlers=handlers,
    )
