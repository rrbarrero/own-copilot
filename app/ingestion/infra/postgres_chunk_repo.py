import json

from psycopg_pool import AsyncConnectionPool

from app.ingestion.domain.chunk_repo_proto import ChunkRepoProto


class PostgresChunkRepo(ChunkRepoProto):
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

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
