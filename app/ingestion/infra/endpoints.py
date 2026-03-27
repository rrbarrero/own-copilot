import hashlib
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.factory import create_document_repo, create_storage_repo
from app.ingestion.domain.document import (
    Document,
    DocumentType,
    ProcessingStatus,
    SourceType,
)
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.domain.storage_repo_proto import StorageRepoProto
from app.ingestion.infra.dtos import DocumentResponseDTO

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

ALLOWED_EXTENSIONS = {
    "md": DocumentType.MARKDOWN,
    "txt": DocumentType.TEXT,
    "json": DocumentType.CONFIG,
    "yml": DocumentType.CONFIG,
    "yaml": DocumentType.CONFIG,
    "py": DocumentType.CODE,
    "ts": DocumentType.CODE,
    "go": DocumentType.CODE,
}

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
MAX_FILES = 10


@router.post("/upload", response_model=list[DocumentResponseDTO])
async def upload_files(
    files: Annotated[
        list[UploadFile], File(description="Upload up to 10 files (max 1MB each)")
    ],
    doc_repo: Annotated[DocumentRepoProto, Depends(create_document_repo)],
    storage_repo: Annotated[StorageRepoProto, Depends(create_storage_repo)],
) -> list[DocumentResponseDTO]:
    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400, detail=f"Maximum {MAX_FILES} files allowed."
        )

    responses = []
    batch_id = uuid.uuid4()
    now = datetime.now(UTC)

    for file in files:
        if not file.filename:
            continue

        # Extension validation
        ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"File {file.filename} extension not allowed. "
                    f"Allowed: {list(ALLOWED_EXTENSIONS.keys())}"
                ),
            )

        # Size validation (rough check by reading)
        content_bytes = await file.read()
        size_bytes = len(content_bytes)
        if size_bytes > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {file.filename} exceeds the maximum size of 1MB.",
            )

        content = content_bytes.decode("utf-8")
        doc_uuid = uuid.uuid4()
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        # Domain Object creation with new fields
        document = Document(
            uuid=doc_uuid,
            source_type=SourceType.UPLOAD,
            source_id=file.filename,
            path=f"uploads/{doc_uuid}/{file.filename}",
            filename=file.filename,
            extension=ext,
            doc_type=ALLOWED_EXTENSIONS[ext],
            processing_status=ProcessingStatus.PENDING,
            size_bytes=size_bytes,
            created_at=now,
            updated_at=now,
            upload_batch_id=batch_id,
            content_hash=content_hash,
            mime_type=file.content_type,
        )

        # Persistence
        await doc_repo.save(document)
        storage_repo.save(document.path, content)

        responses.append(DocumentResponseDTO(uuid=doc_uuid, filename=file.filename))

    return responses
