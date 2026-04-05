import asyncio
import os
import sys
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from uuid import UUID

import psycopg
import pytest
import pytest_asyncio
from psycopg import sql

from app.factory import (
    create_document_repo,
    create_repository_sync_repo,
    create_request_repository_sync,
)
from app.infra.db import Database
from app.ingestion.domain.document import DocumentStatus
from app.repositories.domain.repository_sync import RepositorySyncStatus


@dataclass(frozen=True)
class SharedIndexedRepo:
    repository_id: UUID


@pytest_asyncio.fixture(autouse=True)
async def clear_database(
    request: pytest.FixtureRequest,
) -> AsyncGenerator[None]:
    """
    Automatically runs before every integration test to wipe the database.
    Ensures a clean state for every test scenario.
    """
    if "shared_ingestion" in request.keywords:
        yield
        return

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


@pytest_asyncio.fixture(scope="session")
async def shared_indexed_repo() -> AsyncGenerator[SharedIndexedRepo]:
    """
    Build one expensive E2E repository snapshot/index once per test session and
    reuse it across marked tests to avoid repeating RAPTOR summarization work.
    """
    if os.environ.get("TESTING") != "true":
        pytest.skip("E2E tests require TESTING=true to avoid data loss.")

    pool = Database.get_pool()
    await pool.open()

    repo_url = "https://github.com/rrbarrero/credit-fraud.git"
    sync_service = create_request_repository_sync()
    sync_repo = create_repository_sync_repo()
    doc_repo = create_document_repo()

    result = await sync_service.execute(clone_url=repo_url)
    repo_id = result.repository_id

    sync_completed = False
    docs_ready = False
    timeout = 60 * 20
    interval = 10
    elapsed = 0

    while elapsed < timeout:
        last_sync = await sync_repo.get_latest_by_repository_id(repo_id)
        if last_sync:
            if last_sync.status == RepositorySyncStatus.COMPLETED:
                sync_completed = True
            elif last_sync.status == RepositorySyncStatus.FAILED:
                pytest.fail(f"Sync failed for repository: {last_sync.last_error}")

        if sync_completed:
            docs = await doc_repo.list_by_repository_id(repo_id)
            ready_docs = [
                d for d in docs if d.processing_status == DocumentStatus.READY
            ]
            if ready_docs:
                docs_ready = True
                break

        await asyncio.sleep(interval)
        elapsed += interval

    if not sync_completed:
        pytest.fail(f"Shared repo sync timed out after {timeout}s.")

    if not docs_ready:
        pytest.fail(f"Shared repository indexing timed out after {timeout}s.")

    yield SharedIndexedRepo(repository_id=repo_id)

    await Database.close()
