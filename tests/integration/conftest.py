import os

import psycopg
import pytest_asyncio


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

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgres://postgres:postgres@db:5432/postgres?sslmode=disable",
    )
    
    # Run the truncation using a completely independent connection
    # so we do not mess with the existing global pool.
    conn = await psycopg.AsyncConnection.connect(db_url)
    async with conn.cursor() as cur:
        await cur.execute("TRUNCATE TABLE document_chunks CASCADE;")
        await cur.execute("TRUNCATE TABLE documents CASCADE;")
        await cur.execute("TRUNCATE TABLE ingestion_jobs CASCADE;")
    await conn.commit()
    await conn.close()

    yield

    # Teardown
    conn = await psycopg.AsyncConnection.connect(db_url)
    async with conn.cursor() as cur:
        await cur.execute("TRUNCATE TABLE document_chunks CASCADE;")
        await cur.execute("TRUNCATE TABLE documents CASCADE;")
        await cur.execute("TRUNCATE TABLE ingestion_jobs CASCADE;")
    await conn.commit()
    await conn.close()
