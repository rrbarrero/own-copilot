import json

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.schemas.chat import ChatScope, ScopeType


class PostgresRetrievalRepo:
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def search(
        self,
        query_embedding: list[float],
        scope: ChatScope,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            # Base query with vector similarity
            # 1 - (<=>) is cosine similarity in pgvector
            # We explicitly cast to ::vector for the operator to match
            query = """
                SELECT
                    dc.document_uuid,
                    dc.chunk_index,
                    dc.content,
                    dc.metadata,
                    d.path,
                    d.filename,
                    d.source_type,
                    d.repository_id,
                    1 - (dc.embedding <=> %(query_embedding)s::vector) AS score
                FROM document_chunks dc
                JOIN documents d ON d.uuid = dc.document_uuid
                WHERE 1=1
            """
            params: dict[str, str | int | list[float]] = {
                "query_embedding": query_embedding,
                "top_k": top_k,
            }

            # Apply scope filters
            if scope.type == ScopeType.REPOSITORY:
                query += " AND d.repository_id = %(repository_id)s"
                params["repository_id"] = str(scope.repository_id)
            elif scope.type == ScopeType.DOCUMENT:
                query += " AND d.uuid = %(document_uuid)s"
                params["document_uuid"] = str(scope.document_id)

            # Order and limit
            query += (
                " ORDER BY dc.embedding <=> %(query_embedding)s::vector LIMIT %(top_k)s"
            )

            await cur.execute(query, params)
            rows = await cur.fetchall()

            return [
                RetrievedChunk(
                    document_uuid=row["document_uuid"],
                    chunk_index=row["chunk_index"],
                    content=row["content"],
                    path=row["path"],
                    filename=row["filename"],
                    source_type=row["source_type"],
                    repository_id=row["repository_id"],
                    score=float(row["score"]),
                    metadata=row["metadata"]
                    if isinstance(row["metadata"], dict)
                    else json.loads(row["metadata"]),
                )
                for row in rows
            ]
