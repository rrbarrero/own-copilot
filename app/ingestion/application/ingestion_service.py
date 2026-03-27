import hashlib
import uuid
from datetime import UTC, datetime

from app.ingestion.domain.document import Document, ProcessingStatus, SourceType
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.domain.file_validator import AllowedExtension, FileValidator
from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.domain.job_repo_proto import JobRepoProto
from app.ingestion.domain.storage_repo_proto import StorageRepoProto


class IngestionService:
    def __init__(
        self,
        doc_repo: DocumentRepoProto,
        storage_repo: StorageRepoProto,
        job_repo: JobRepoProto,
    ):
        self.doc_repo = doc_repo
        self.storage_repo = storage_repo
        self.job_repo = job_repo

    async def upload_file(
        self,
        filename: str,
        content_bytes: bytes,
        mime_type: str | None,
        batch_id: uuid.UUID,
    ) -> uuid.UUID:
        # Business logic: validate (count/extension) and store raw
        ext = FileValidator.validate_file(filename, content_bytes)
        doc_uuid = uuid.uuid4()
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        now = datetime.now(UTC)

        document = Document(
            uuid=doc_uuid,
            source_type=SourceType.UPLOAD,
            source_id=filename,
            path=f"uploads/{doc_uuid}/{filename}",
            filename=filename,
            extension=ext,
            doc_type=AllowedExtension.get_doc_type(ext),
            processing_status=ProcessingStatus.PENDING,
            size_bytes=len(content_bytes),
            created_at=now,
            updated_at=now,
            upload_batch_id=batch_id,
            content_hash=content_hash,
            mime_type=mime_type,
        )

        # Store metadata and RAW bytes
        await self.doc_repo.save(document)
        self.storage_repo.save(document.path, content_bytes)

        # Create background job for processing (decoding/chunking/indexing)
        job = Job(
            id=uuid.uuid4(),
            queue_name="ingestion",
            job_type="process_document",
            payload={"doc_uuid": str(doc_uuid)},
            status=JobStatus.PENDING,
            attempts=0,
            max_attempts=5,
            run_at=now,
            created_at=now,
            updated_at=now,
            priority=0,
            correlation_id=batch_id,
        )
        await self.job_repo.save(job)

        return doc_uuid

    async def get_batch_documents(self, batch_id: uuid.UUID) -> list[Document]:
        return await self.doc_repo.get_by_batch_id(batch_id)
