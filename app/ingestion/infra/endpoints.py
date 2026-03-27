from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile

from app.factory import create_ingestion_service
from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.domain.file_validator import FileValidationError, FileValidator
from app.ingestion.infra.dtos import DocumentResponseDTO

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/upload", response_model=list[DocumentResponseDTO])
async def upload_files(
    files: list[UploadFile] = File(...),  # noqa: B008
    x_idempotency_key: Annotated[UUID, Header(alias="X-Idempotency-Key")] = None,  # type: ignore
    service: Annotated[IngestionService, Depends(create_ingestion_service)] = None,  # type: ignore
) -> list[DocumentResponseDTO]:
    # Check idempotency
    if not x_idempotency_key:
        raise HTTPException(status_code=422, detail="X-Idempotency-Key is required")

    existing_docs = await service.get_batch_documents(x_idempotency_key)
    if existing_docs:
        return [
            DocumentResponseDTO(
                uuid=doc.uuid, filename=doc.filename, status="already_processed"
            )
            for doc in existing_docs
        ]

    try:
        FileValidator.validate_count(len(files))
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=e.message) from e

    responses = []
    batch_id = x_idempotency_key

    for file in files:
        if not file.filename:
            continue

        try:
            content_bytes = await file.read()
            doc_uuid = await service.upload_file(
                filename=file.filename,
                content_bytes=content_bytes,
                mime_type=file.content_type,
                batch_id=batch_id,
            )
            responses.append(DocumentResponseDTO(uuid=doc_uuid, filename=file.filename))
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=e.message) from e
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error processing {file.filename}: {str(e)}"
            ) from e

    return responses
