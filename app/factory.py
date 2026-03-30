from functools import lru_cache

from app.config import settings
from app.conversation.application.chat_service import ChatService
from app.conversation.application.question_rewriter import QuestionRewriter
from app.conversation.domain.conversation_repo_proto import ConversationRepoProto
from app.conversation.infra.postgres_conversation_repo import (
    PostgresConversationRepo,
)
from app.core.llm import get_llm
from app.infra.db import Database
from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.domain.chunk_repo_proto import ChunkRepoProto
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.domain.job_repo_proto import JobRepoProto
from app.ingestion.domain.storage_repo_proto import StorageRepoProto
from app.ingestion.infra.in_filesystem_storage_repo import InFilesystemStorageRepo
from app.ingestion.infra.postgres_chunk_repo import PostgresChunkRepo
from app.ingestion.infra.postgres_document_repo import PostgresDocumentRepo
from app.ingestion.infra.postgres_job_repo import PostgresJobRepo
from app.repositories.application.request_repository_sync import (
    RequestRepositorySync,
)
from app.repositories.domain.repository_repo_proto import RepositoryRepoProto
from app.repositories.domain.repository_sync_repo_proto import (
    RepositorySyncRepoProto,
)
from app.repositories.infra.postgres_repository_repo import (
    PostgresRepositoryRepo,
)
from app.repositories.infra.postgres_repository_sync_repo import (
    PostgresRepositorySyncRepo,
)
from app.repositories.infra.repository_url_normalizer import (
    RepositoryUrlNormalizer,
)
from app.retrieval.application.chat_with_citations import ChatWithCitations
from app.retrieval.application.retriever import Retriever
from app.retrieval.infra.ollama_query_embedding_service import (
    OllamaQueryEmbeddingService,
)
from app.retrieval.infra.postgres_retrieval_repo import PostgresRetrievalRepo


@lru_cache
def create_llm():
    return get_llm()


def create_document_repo() -> DocumentRepoProto:
    return PostgresDocumentRepo(Database.get_pool())


def create_chunk_repo() -> ChunkRepoProto:
    return PostgresChunkRepo(Database.get_pool())


def create_storage_repo() -> StorageRepoProto:
    return InFilesystemStorageRepo(settings.STORAGE_PATH)


def create_job_repo() -> JobRepoProto:
    return PostgresJobRepo(Database.get_pool())


def create_repository_repo() -> RepositoryRepoProto:
    return PostgresRepositoryRepo(Database.get_pool())


def create_repository_sync_repo() -> RepositorySyncRepoProto:
    return PostgresRepositorySyncRepo(Database.get_pool())


def create_request_repository_sync() -> RequestRepositorySync:
    return RequestRepositorySync(
        repository_repo=create_repository_repo(),
        job_repo=create_job_repo(),
        url_normalizer=RepositoryUrlNormalizer(),
        # Use STORAGE_PATH/checkouts for git roots
        checkouts_root=f"{settings.STORAGE_PATH}/checkouts",
    )


def create_ingestion_service() -> IngestionService:
    return IngestionService(
        doc_repo=create_document_repo(),
        storage_repo=create_storage_repo(),
        job_repo=create_job_repo(),
    )


def create_retrieval_repo():
    return PostgresRetrievalRepo(Database.get_pool())


@lru_cache
def create_query_embedding_service():
    return OllamaQueryEmbeddingService(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


@lru_cache
def create_retriever():
    return Retriever(
        retrieval_repo=create_retrieval_repo(),
        embedding_service=create_query_embedding_service(),
        threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD,
    )


@lru_cache
def create_chat_with_citations():
    return ChatWithCitations(
        retriever=create_retriever(),
        llm=create_llm(),
    )


def create_conversation_repo() -> ConversationRepoProto:
    return PostgresConversationRepo(Database.get_pool())


@lru_cache
def create_question_rewriter():
    return QuestionRewriter(llm=create_llm())


@lru_cache
def create_chat_service():
    return ChatService(
        conversation_repo=create_conversation_repo(),
        question_rewriter=create_question_rewriter(),
        chat_with_citations=create_chat_with_citations(),
    )
