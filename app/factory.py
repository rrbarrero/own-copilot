from app.config import settings
from app.core.llm import llm
from app.infra.db import get_db_pool
from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.domain.chunk_repo_proto import ChunkRepoProto
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.domain.job_repo_proto import JobRepoProto
from app.ingestion.domain.storage_repo_proto import StorageRepoProto
from app.ingestion.infra.in_filesystem_storage_repo import InFilesystemStorageRepo
from app.ingestion.infra.postgres_document_repo import PostgresDocumentRepo
from app.ingestion.infra.postgres_job_repo import PostgresJobRepo


def create_llm():
    return llm


def create_document_repo() -> DocumentRepoProto:
    return PostgresDocumentRepo(get_db_pool())


def create_chunk_repo() -> ChunkRepoProto:
    # PostgresDocumentRepo currently implements both.
    return PostgresDocumentRepo(get_db_pool())


def create_storage_repo() -> StorageRepoProto:
    return InFilesystemStorageRepo(settings.STORAGE_PATH)


def create_job_repo() -> JobRepoProto:
    return PostgresJobRepo(get_db_pool())


def create_ingestion_service() -> IngestionService:
    return IngestionService(
        doc_repo=create_document_repo(),
        storage_repo=create_storage_repo(),
        job_repo=create_job_repo(),
    )
