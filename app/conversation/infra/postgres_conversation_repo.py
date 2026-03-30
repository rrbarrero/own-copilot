import json
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.conversation.domain.conversation import Conversation
from app.conversation.domain.conversation_message import ConversationMessage


class PostgresConversationRepo:
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM conversations WHERE id = %(id)s",
                {"id": str(conversation_id)},
            )
            row = await cur.fetchone()
            if not row:
                return None
            return Conversation(
                id=row["id"],
                scope_type=row["scope_type"],
                repository_id=row["repository_id"],
                document_id=row["document_id"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    async def create(self, conversation: Conversation) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO conversations (id, scope_type, repository_id,
                                          document_id, created_at, updated_at)
                VALUES (%(id)s, %(scope_type)s, %(repository_id)s,
                        %(document_id)s, %(created_at)s, %(updated_at)s)
                """,
                {
                    "id": str(conversation.id),
                    "scope_type": conversation.scope_type,
                    "repository_id": str(conversation.repository_id)
                    if conversation.repository_id
                    else None,
                    "document_id": str(conversation.document_id)
                    if conversation.document_id
                    else None,
                    "created_at": conversation.created_at,
                    "updated_at": conversation.updated_at,
                },
            )

    async def add_message(self, message: ConversationMessage) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO conversation_messages (id, conversation_id, role, content,
                                                  rewritten_question, citations_json,
                                                  created_at)
                VALUES (%(id)s, %(conversation_id)s, %(role)s, %(content)s,
                        %(rewritten_question)s, %(citations_json)s, %(created_at)s)
                """,
                {
                    "id": str(message.id),
                    "conversation_id": str(message.conversation_id),
                    "role": message.role,
                    "content": message.content,
                    "rewritten_question": message.rewritten_question,
                    "citations_json": json.dumps(message.citations_json, default=str)
                    if message.citations_json
                    else None,
                    "created_at": message.created_at,
                },
            )

    async def get_recent_messages(
        self, conversation_id: UUID, limit: int = 8
    ) -> list[ConversationMessage]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                """
                SELECT * FROM conversation_messages
                WHERE conversation_id = %(id)s
                ORDER BY created_at DESC
                LIMIT %(limit)s
                """,
                {"id": str(conversation_id), "limit": limit},
            )
            rows = await cur.fetchall()
            # Descending from query, so reversed to be ascending in history
            rows.reverse()
            return [
                ConversationMessage(
                    id=row["id"],
                    conversation_id=row["conversation_id"],
                    role=row["role"],
                    content=row["content"],
                    rewritten_question=row["rewritten_question"],
                    citations_json=row["citations_json"]
                    if isinstance(row["citations_json"], list)
                    or row["citations_json"] is None
                    else json.loads(str(row["citations_json"])),
                    created_at=row["created_at"],
                )
                for row in rows
            ]
