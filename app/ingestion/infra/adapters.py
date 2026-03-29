from uuid import UUID

from app.ingestion.domain.document import (
    Document,
    DocumentStatus,
    DocumentType,
    SourceType,
)


def document_row_adapter(row: dict) -> Document:
    """
    Adapter to convert a database row (dict) from the documents table
    to a domain Document entity.
    """
    return Document(
        uuid=UUID(str(row["uuid"])),
        source_type=SourceType(str(row["source_type"])),
        source_id=str(row["source_id"]),
        path=str(row["path"]),
        filename=str(row["filename"]),
        extension=str(row["extension"]),
        doc_type=DocumentType(str(row["doc_type"])),
        processing_status=DocumentStatus(str(row["processing_status"])),
        size_bytes=int(row["size_bytes"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        language=row.get("language"),
        upload_batch_id=UUID(str(row["upload_batch_id"]))
        if row.get("upload_batch_id")
        else None,
        repository_sync_id=UUID(str(row["repository_sync_id"]))
        if row.get("repository_sync_id")
        else None,
        repository_id=UUID(str(row["repository_id"]))
        if row.get("repository_id")
        else None,
        repository_url=row.get("repository_url"),
        content_hash=row.get("content_hash"),
        branch=row.get("branch"),
        mime_type=row.get("mime_type"),
        indexed_at=row.get("indexed_at"),
        last_error=row.get("last_error"),
        version=int(row.get("version", 1)),
        superseded_by=UUID(str(row["superseded_by"]))
        if row.get("superseded_by")
        else None,
    )
