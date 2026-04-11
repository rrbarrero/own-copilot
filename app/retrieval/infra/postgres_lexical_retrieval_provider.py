import json
import re

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.schemas.chat import ChatScope, ScopeType


class PostgresLexicalRetrievalProvider:
    _MAX_TERMS = 8
    _MIN_TRIGRAM_SIMILARITY = 0.18
    _TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]{2,}")
    _STOPWORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "defined",
        "do",
        "does",
        "explain",
        "find",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "primary",
        "responsibility",
        "show",
        "tell",
        "that",
        "the",
        "this",
        "to",
        "traditional",
        "what",
        "where",
        "which",
        "who",
        "why",
    }

    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    def _extract_terms(self, question: str) -> list[str]:
        prioritized_terms: list[str] = []
        secondary_terms: list[str] = []
        seen: set[str] = set()
        has_code_like_signal = False

        for term in self._TOKEN_RE.findall(question):
            lowered = term.lower()
            if lowered in seen or lowered in self._STOPWORDS:
                continue
            seen.add(lowered)

            is_code_like = (
                any(char in term for char in "_./:-")
                or any(char.isdigit() for char in term)
                or (
                    any(char.isupper() for char in term)
                    and any(char.islower() for char in term)
                )
            )

            if is_code_like:
                has_code_like_signal = True
                prioritized_terms.append(term)
            else:
                secondary_terms.append(term)

        if not has_code_like_signal:
            return []

        return (prioritized_terms + secondary_terms)[: self._MAX_TERMS]

    async def search(
        self,
        question: str,
        scope: ChatScope,
        top_k: int = 5,
    ) -> list[RetrievedChunk]:
        terms = self._extract_terms(question)
        if not terms:
            return []

        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            query = """
                WITH query_input AS (
                    SELECT
                        %(question)s::text AS question,
                        %(terms)s::text[] AS terms,
                        websearch_to_tsquery('simple', %(question)s) AS ts_query
                )
                SELECT
                    dc.document_uuid,
                    dc.chunk_index,
                    dc.content,
                    dc.metadata,
                    d.path,
                    d.filename,
                    d.source_type,
                    d.repository_id,
                    (
                        CASE
                            WHEN lower(dc.content) LIKE
                                '%%' || lower(q.question) || '%%'
                            THEN 4.0
                            ELSE 0.0
                        END
                        + CASE
                            WHEN lower(d.path) LIKE
                                '%%' || lower(q.question) || '%%'
                              OR lower(d.filename) LIKE
                                '%%' || lower(q.question) || '%%'
                            THEN 6.0
                            ELSE 0.0
                        END
                        + (
                            SELECT COALESCE(SUM(
                                CASE
                                    WHEN lower(dc.content) LIKE
                                        '%%' || lower(term) || '%%'
                                    THEN 0.9
                                    ELSE 0.0
                                END
                                + CASE
                                    WHEN lower(d.path) LIKE
                                        '%%' || lower(term) || '%%'
                                      OR lower(d.filename) LIKE
                                        '%%' || lower(term) || '%%'
                                    THEN 1.5
                                    ELSE 0.0
                                END
                            ), 0.0)
                            FROM unnest(q.terms) AS term
                        )
                        + 1.5 * ts_rank_cd(
                            to_tsvector('simple', dc.content),
                            q.ts_query
                        )
                        + 2.0 * GREATEST(
                            similarity(lower(dc.content), lower(q.question)),
                            similarity(lower(d.path), lower(q.question)),
                            similarity(lower(d.filename), lower(q.question))
                        )
                    ) AS score
                FROM document_chunks dc
                JOIN documents d ON d.uuid = dc.document_uuid
                CROSS JOIN query_input q
                WHERE (
                    to_tsvector('simple', dc.content) @@ q.ts_query
                    OR EXISTS (
                        SELECT 1
                        FROM unnest(q.terms) AS term
                        WHERE lower(dc.content) LIKE '%%' || lower(term) || '%%'
                           OR lower(d.path) LIKE '%%' || lower(term) || '%%'
                           OR lower(d.filename) LIKE '%%' || lower(term) || '%%'
                    )
                    OR GREATEST(
                        similarity(lower(dc.content), lower(q.question)),
                        similarity(lower(d.path), lower(q.question)),
                        similarity(lower(d.filename), lower(q.question))
                    ) >= %(min_similarity)s
                )
            """
            params: dict[str, str | int | float | list[str]] = {
                "question": question,
                "terms": terms,
                "top_k": top_k,
                "min_similarity": self._MIN_TRIGRAM_SIMILARITY,
            }

            if scope.type == ScopeType.REPOSITORY:
                query += " AND d.repository_id = %(repository_id)s"
                params["repository_id"] = str(scope.repository_id)
                if scope.repository_sync_id:
                    query += " AND d.repository_sync_id = %(repository_sync_id)s"
                    params["repository_sync_id"] = str(scope.repository_sync_id)
            elif scope.type == ScopeType.DOCUMENT:
                query += " AND d.uuid = %(document_uuid)s"
                params["document_uuid"] = str(scope.document_id)

            query += " ORDER BY score DESC LIMIT %(top_k)s"

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
