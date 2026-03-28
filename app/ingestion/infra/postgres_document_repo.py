import json
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.ingestion.domain.chunk_repo_proto import ChunkRepoProto
from app.ingestion.domain.document import (
    Document,
)
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.infra.adapters import document_row_adapter


class PostgresDocumentRepo(DocumentRepoProto, ChunkRepoProto):
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def save(self, document: Document) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO documents (
                    uuid, source_type, source_id, path, filename, extension,
                    doc_type, processing_status, size_bytes, created_at,
                    updated_at, language, upload_batch_id, repository_sync_id,
                    repository_url, content_hash, branch, mime_type,
                    indexed_at, last_error, version, superseded_by
                ) VALUES (
                    %(uuid)s, %(source_type)s, %(source_id)s, %(path)s,
                    %(filename)s, %(extension)s, %(doc_type)s,
                    %(processing_status)s, %(size_bytes)s, %(created_at)s,
                    %(updated_at)s, %(language)s, %(upload_batch_id)s,
                    %(repository_sync_id)s, %(repository_url)s,
                    %(content_hash)s, %(branch)s, %(mime_type)s,
                    %(indexed_at)s, %(last_error)s, %(version)s,
                    %(superseded_by)s
                )
                ON CONFLICT (uuid) DO UPDATE SET
                    source_type = EXCLUDED.source_type,
                    source_id = EXCLUDED.source_id,
                    path = EXCLUDED.path,
                    filename = EXCLUDED.filename,
                    extension = EXCLUDED.extension,
                    doc_type = EXCLUDED.doc_type,
                    processing_status = EXCLUDED.processing_status,
                    size_bytes = EXCLUDED.size_bytes,
                    updated_at = EXCLUDED.updated_at,
                    language = EXCLUDED.language,
                    upload_batch_id = EXCLUDED.upload_batch_id,
                    repository_sync_id = EXCLUDED.repository_sync_id,
                    repository_url = EXCLUDED.repository_url,
                    content_hash = EXCLUDED.content_hash,
                    branch = EXCLUDED.branch,
                    mime_type = EXCLUDED.mime_type,
                    indexed_at = EXCLUDED.indexed_at,
                    last_error = EXCLUDED.last_error,
                    version = EXCLUDED.version,
                    superseded_by = EXCLUDED.superseded_by;
                """,
                {
                    "uuid": str(document.uuid),
                    "source_type": document.source_type.value,
                    "source_id": document.source_id,
                    "path": document.path,
                    "filename": document.filename,
                    "extension": document.extension,
                    "doc_type": document.doc_type.value,
                    "processing_status": document.processing_status.value,
                    "size_bytes": document.size_bytes,
                    "created_at": document.created_at,
                    "updated_at": document.updated_at,
                    "language": document.language,
                    "upload_batch_id": str(document.upload_batch_id)
                    if document.upload_batch_id
                    else None,
                    "repository_sync_id": str(document.repository_sync_id)
                    if document.repository_sync_id
                    else None,
                    "repository_id": str(document.repository_id)
                    if document.repository_id
                    else None,
                    "repository_url": document.repository_url,
                    "content_hash": document.content_hash,
                    "branch": document.branch,
                    "mime_type": document.mime_type,
                    "indexed_at": document.indexed_at,
                    "last_error": document.last_error,
                    "version": document.version,
                    "superseded_by": str(document.superseded_by)
                    if document.superseded_by
                    else None,
                },
            )

    async def get_by_uuid(self, uuid: str) -> Document | None:
        try:
            doc_uuid = UUID(uuid)
        except ValueError:
            return None

        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM documents WHERE uuid = %s", (str(doc_uuid),)
            )
            row = await cur.fetchone()
            if not row:
                return None

            return document_row_adapter(row)

    async def get_by_batch_id(self, batch_id: UUID) -> list[Document]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM documents WHERE upload_batch_id = %s",
                (str(batch_id),),
            )
            rows = await cur.fetchall()
            return [document_row_adapter(row) for row in rows]

    async def list_by_repository_sync_id(self, sync_id: UUID) -> list[Document]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM documents WHERE repository_sync_id = %s",
                (str(sync_id),),
            )
            rows = await cur.fetchall()
            return [document_row_adapter(row) for row in rows]

    async def get_by_repository_and_source_id(
        self, repository_id: UUID, source_id: str
    ) -> Document | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM documents WHERE repository_id = %s AND source_id = %s",
                (str(repository_id), source_id),
            )
            row = await cur.fetchone()
            return document_row_adapter(row) if row else None

    async def list_by_repository_id(self, repository_id: UUID) -> list[Document]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM documents WHERE repository_id = %s",
                (str(repository_id),),
            )
            rows = await cur.fetchall()
            return [document_row_adapter(row) for row in rows]

    async def delete_by_uuids(self, uuids: list[UUID]) -> None:
        if not uuids:
            return
        async with (
            self._pool.connection() as conn,
            conn.cursor() as cur,
        ):
            await cur.execute(
                "DELETE FROM documents WHERE uuid = ANY(%s)",
                ([str(u) for u in uuids],),
            )

    async def save_chunks(self, document_uuid: str, chunks: list[dict]) -> None:
        async with (
            self._pool.connection() as conn,
            conn.transaction(),
            conn.cursor() as cur,
        ):
            # 1. First, delete existing chunks for this document (idempotency)
            await cur.execute(
                "DELETE FROM document_chunks WHERE document_uuid = %s",
                (str(document_uuid),),
            )

            # 2. Batch insert new chunks
            rows = []
            for chunk in chunks:
                rows.append(
                    (
                        str(document_uuid),
                        chunk["chunk_index"],
                        chunk["content"],
                        chunk.get("embedding"),
                        json.dumps(chunk.get("metadata", {})),
                    )
                )

            if rows:
                await cur.executemany(
                    """
                    INSERT INTO document_chunks (
                        document_uuid, chunk_index, content, embedding, metadata
                    ) VALUES (%s, %s, %s, %s, %s)
                    """,
                    rows,
                )
