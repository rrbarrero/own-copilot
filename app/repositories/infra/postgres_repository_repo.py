from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.repositories.domain.repository import Repository
from app.repositories.domain.repository_repo_proto import RepositoryRepoProto


class PostgresRepositoryRepo(RepositoryRepoProto):
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def save(self, repository: Repository) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO repositories (
                    id, provider, clone_url, normalized_clone_url, owner, name,
                    default_branch, local_path, is_active, last_synced_at,
                    created_at, updated_at
                ) VALUES (
                    %(id)s, %(provider)s, %(clone_url)s, %(normalized_clone_url)s,
                    %(owner)s, %(name)s, %(default_branch)s, %(local_path)s,
                    %(is_active)s, %(last_synced_at)s, %(created_at)s, %(updated_at)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    provider = EXCLUDED.provider,
                    clone_url = EXCLUDED.clone_url,
                    normalized_clone_url = EXCLUDED.normalized_clone_url,
                    owner = EXCLUDED.owner,
                    name = EXCLUDED.name,
                    default_branch = EXCLUDED.default_branch,
                    local_path = EXCLUDED.local_path,
                    is_active = EXCLUDED.is_active,
                    last_synced_at = EXCLUDED.last_synced_at,
                    updated_at = EXCLUDED.updated_at;
                """,
                {
                    "id": str(repository.id),
                    "provider": repository.provider,
                    "clone_url": repository.clone_url,
                    "normalized_clone_url": repository.normalized_clone_url,
                    "owner": repository.owner,
                    "name": repository.name,
                    "default_branch": repository.default_branch,
                    "local_path": repository.local_path,
                    "is_active": repository.is_active,
                    "last_synced_at": repository.last_synced_at,
                    "created_at": repository.created_at,
                    "updated_at": repository.updated_at,
                },
            )

    async def get_by_id(self, repository_id: UUID) -> Repository | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM repositories WHERE id = %s", (str(repository_id),)
            )
            row = await cur.fetchone()
            return self._row_to_entity(row) if row else None

    async def get_by_normalized_url(self, normalized_url: str) -> Repository | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM repositories WHERE normalized_clone_url = %s",
                (normalized_url,),
            )
            row = await cur.fetchone()
            return self._row_to_entity(row) if row else None

    async def list_all(self) -> list[Repository]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute("SELECT * FROM repositories")
            rows = await cur.fetchall()
            return [self._row_to_entity(row) for row in rows]

    def _row_to_entity(self, row: dict) -> Repository:
        return Repository(
            id=UUID(str(row["id"])),
            provider=str(row["provider"]),
            clone_url=str(row["clone_url"]),
            normalized_clone_url=str(row["normalized_clone_url"]),
            owner=str(row["owner"]),
            name=str(row["name"]),
            local_path=str(row["local_path"]),
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            default_branch=row.get("default_branch"),
            last_synced_at=row.get("last_synced_at"),
        )
