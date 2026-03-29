from psycopg_pool import AsyncConnectionPool

from app.config import settings


class Database:
    """
    Manages the Postgres database connection pool.
    This encapsulates the global state and provides a cleaner interface
    than raw global variables.
    """

    _pool: AsyncConnectionPool | None = None

    @classmethod
    def get_pool(cls) -> AsyncConnectionPool:
        if cls._pool is None:
            cls._pool = AsyncConnectionPool(
                conninfo=settings.DATABASE_URL,
                min_size=2,
                max_size=10,
                open=False,  # Lifecycle is managed via open/close
            )
        return cls._pool

    @classmethod
    async def get_embedding_dimension(cls) -> int:
        if cls._pool is None:
            raise RuntimeError("Database pool not initialized")
        async with (
            cls._pool.connection() as conn,
            conn.cursor() as cur,
        ):
            # Query for the dimension of the embedding column
            await cur.execute(
                """
                SELECT atttypmod
                FROM pg_attribute
                WHERE attrelid = 'public.document_chunks'::regclass
                AND attname = 'embedding'
            """
            )
            row = await cur.fetchone()
            if row and row[0] != -1:
                return row[0]
            return -1

    @classmethod
    async def close(cls) -> None:
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None

    @classmethod
    def is_open(cls) -> bool:
        return cls._pool is not None
