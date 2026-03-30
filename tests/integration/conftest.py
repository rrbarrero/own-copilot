import os
import sys

import psycopg
import pytest_asyncio
from psycopg import sql


@pytest_asyncio.fixture(autouse=True)
async def clear_database():
    """
    Automatically runs before every integration test to wipe the database.
    Ensures a clean state for every test scenario.
    """
    if os.environ.get("TESTING") != "true":
        raise RuntimeError(
            "FATAL: Database wipe attempted without TESTING=true. "
            "Aborting to protect production data."
        )

    # Use DELETE instead of TRUNCATE to avoid exclusive table locks that hang
    # when other connections (app pool, worker) are active in Docker environments.
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgres://postgres:postgres@db:5432/postgres?sslmode=disable",
    )

    tables = [
        "conversation_messages",
        "conversations",
        "document_chunks",
        "documents",
        "ingestion_jobs",
        "repository_syncs",
        "repositories",
    ]

    try:
        # Use an independent connection to ensure we do not mess with the pool
        async with await psycopg.AsyncConnection.connect(db_url) as conn:
            async with conn.cursor() as cur:
                # Ordering to satisfy foreign key constraints: children before parents
                for table_name in tables:
                    # Using psycopg.sql.SQL to satisfy Pyrefly's overload matcher
                    query = sql.SQL("DELETE FROM {table};").format(
                        table=sql.Identifier(table_name)
                    )
                    await cur.execute(query)
            await conn.commit()
    except Exception as e:
        # Minimal warning during tests if connection is lost
        print(f"WARNING: Database wipe failed: {e}", file=sys.stderr)

    yield
