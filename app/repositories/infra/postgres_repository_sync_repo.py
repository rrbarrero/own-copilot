from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.repositories.domain.repository_sync import RepositorySync, RepositorySyncStatus
from app.repositories.domain.repository_sync_repo_proto import RepositorySyncRepoProto


class PostgresRepositorySyncRepo(RepositorySyncRepoProto):
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def save(self, sync: RepositorySync) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO repository_syncs (
                    id, repository_id, branch, commit_sha, status, started_at,
                    finished_at, last_error, scanned_files, changed_files,
                    deleted_files, created_at, updated_at
                ) VALUES (
                    %(id)s, %(repository_id)s, %(branch)s, %(commit_sha)s,
                    %(status)s, %(started_at)s, %(finished_at)s, %(last_error)s,
                    %(scanned_files)s, %(changed_files)s, %(deleted_files)s,
                    %(created_at)s, %(updated_at)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    commit_sha = EXCLUDED.commit_sha,
                    status = EXCLUDED.status,
                    finished_at = EXCLUDED.finished_at,
                    last_error = EXCLUDED.last_error,
                    scanned_files = EXCLUDED.scanned_files,
                    changed_files = EXCLUDED.changed_files,
                    deleted_files = EXCLUDED.deleted_files,
                    updated_at = EXCLUDED.updated_at;
                """,
                {
                    "id": str(sync.id),
                    "repository_id": str(sync.repository_id),
                    "branch": sync.branch,
                    "commit_sha": sync.commit_sha,
                    "status": sync.status.value,
                    "started_at": sync.started_at,
                    "finished_at": sync.finished_at,
                    "last_error": sync.last_error,
                    "scanned_files": sync.scanned_files,
                    "changed_files": sync.changed_files,
                    "deleted_files": sync.deleted_files,
                    "created_at": sync.created_at,
                    "updated_at": sync.updated_at,
                },
            )

    async def get_by_id(self, sync_id: UUID) -> RepositorySync | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM repository_syncs WHERE id = %s", (str(sync_id),)
            )
            row = await cur.fetchone()
            return self._row_to_entity(row) if row else None

    async def get_running_by_repository_id(
        self, repository_id: UUID
    ) -> RepositorySync | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                """
                SELECT * FROM repository_syncs
                WHERE repository_id = %s AND status = 'running'
                """,
                (str(repository_id),),
            )
            row = await cur.fetchone()
            return self._row_to_entity(row) if row else None

    async def get_latest_by_repository_id(
        self, repository_id: UUID
    ) -> RepositorySync | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                """
                SELECT * FROM repository_syncs
                WHERE repository_id = %s ORDER BY created_at DESC LIMIT 1
                """,
                (str(repository_id),),
            )
            row = await cur.fetchone()
            return self._row_to_entity(row) if row else None

    async def get_latest_completed_by_repository_and_branch(
        self, repository_id: UUID, branch: str
    ) -> RepositorySync | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                """
                SELECT * FROM repository_syncs
                WHERE repository_id = %s
                  AND branch = %s
                  AND status = 'completed'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (str(repository_id), branch),
            )
            row = await cur.fetchone()
            return self._row_to_entity(row) if row else None

    async def list_by_repository_id(self, repository_id: UUID) -> list[RepositorySync]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                """
                SELECT * FROM repository_syncs
                WHERE repository_id = %s ORDER BY created_at DESC
                """,
                (str(repository_id),),
            )
            rows = await cur.fetchall()
            return [self._row_to_entity(row) for row in rows]

    def _row_to_entity(self, row: dict) -> RepositorySync:
        return RepositorySync(
            id=UUID(str(row["id"])),
            repository_id=UUID(str(row["repository_id"])),
            branch=str(row["branch"]),
            status=RepositorySyncStatus(str(row["status"])),
            started_at=row["started_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            commit_sha=row.get("commit_sha"),
            finished_at=row.get("finished_at"),
            last_error=row.get("last_error"),
            scanned_files=int(row["scanned_files"]),
            changed_files=int(row["changed_files"]),
            deleted_files=int(row["deleted_files"]),
        )
