from app.config import settings
from app.core.llm import llm
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.domain.storage_repo_proto import StorageRepoProto
from app.ingestion.infra.in_filesystem_storage_repo import InFilesystemStorageRepo
from app.ingestion.infra.postgres_document_repo import PostgresDocumentRepo


def create_llm():
    return llm


def create_document_repo() -> DocumentRepoProto:
    return PostgresDocumentRepo(settings.DATABASE_URL)


def create_storage_repo() -> StorageRepoProto:
    return InFilesystemStorageRepo(settings.STORAGE_PATH)
