import json
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.domain.job_repo_proto import JobRepoProto


class PostgresJobRepo(JobRepoProto):
    def __init__(self, pool: AsyncConnectionPool):
        self._pool = pool

    async def save(self, job: Job) -> None:
        async with self._pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO ingestion_jobs (
                    id, queue_name, job_type, payload, status, attempts,
                    max_attempts, run_at, created_at, updated_at, priority,
                    correlation_id, locked_at, locked_by, last_error,
                    started_at, finished_at
                ) VALUES (
                    %(id)s, %(queue_name)s, %(job_type)s, %(payload)s,
                    %(status)s, %(attempts)s, %(max_attempts)s, %(run_at)s,
                    %(created_at)s, %(updated_at)s, %(priority)s,
                    %(correlation_id)s, %(locked_at)s, %(locked_by)s,
                    %(last_error)s, %(started_at)s, %(finished_at)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    attempts = EXCLUDED.attempts,
                    updated_at = EXCLUDED.updated_at,
                    locked_at = EXCLUDED.locked_at,
                    locked_by = EXCLUDED.locked_by,
                    last_error = EXCLUDED.last_error,
                    started_at = EXCLUDED.started_at,
                    finished_at = EXCLUDED.finished_at;
                """,
                {
                    "id": str(job.id),
                    "queue_name": job.queue_name,
                    "job_type": job.job_type,
                    "payload": json.dumps(job.payload),
                    "status": job.status.value,
                    "attempts": job.attempts,
                    "max_attempts": job.max_attempts,
                    "run_at": job.run_at,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "priority": job.priority,
                    "correlation_id": str(job.correlation_id)
                    if job.correlation_id
                    else None,
                    "locked_at": job.locked_at,
                    "locked_by": job.locked_by,
                    "last_error": job.last_error,
                    "started_at": job.started_at,
                    "finished_at": job.finished_at,
                },
            )

    async def get_by_id(self, job_id: UUID) -> Job | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM ingestion_jobs WHERE id = %s", (str(job_id),)
            )
            row = await cur.fetchone()
            if not row:
                return None

            return Job(
                id=UUID(str(row["id"])),
                queue_name=str(row["queue_name"]),
                job_type=str(row["job_type"]),
                payload=row["payload"]
                if isinstance(row["payload"], dict)
                else json.loads(row["payload"]),
                status=JobStatus(str(row["status"])),
                attempts=int(row["attempts"]),
                max_attempts=int(row["max_attempts"]),
                run_at=row["run_at"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                priority=int(row["priority"]),
                correlation_id=UUID(str(row["correlation_id"]))
                if row.get("correlation_id")
                else None,
                locked_at=row.get("locked_at"),
                locked_by=row.get("locked_by"),
                last_error=row.get("last_error"),
                started_at=row.get("started_at"),
                finished_at=row.get("finished_at"),
            )

    async def claim_next_job(self, queue_name: str, locked_by: str) -> Job | None:
        query = """
        UPDATE ingestion_jobs
        SET status = %s,
            locked_at = NOW(),
            locked_by = %s,
            updated_at = NOW(),
            attempts = attempts + 1
        WHERE id = (
            SELECT id
            FROM ingestion_jobs
            WHERE queue_name = %s
              AND status = %s
              AND run_at <= NOW()
              AND attempts < max_attempts
            ORDER BY priority DESC, created_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        RETURNING *;
        """
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                query,
                (
                    JobStatus.PROCESSING.value,
                    locked_by,
                    queue_name,
                    JobStatus.PENDING.value,
                ),
            )
            row = await cur.fetchone()
            if not row:
                return None

            return Job(
                id=UUID(str(row["id"])),
                queue_name=str(row["queue_name"]),
                job_type=str(row["job_type"]),
                payload=row["payload"],
                status=JobStatus(str(row["status"])),
                attempts=int(row["attempts"]),
                max_attempts=int(row["max_attempts"]),
                run_at=row["run_at"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                priority=int(row["priority"]),
                correlation_id=UUID(str(row["correlation_id"]))
                if row.get("correlation_id")
                else None,
                locked_at=row.get("locked_at"),
                locked_by=row.get("locked_by"),
                last_error=row.get("last_error"),
                started_at=row.get("started_at"),
                finished_at=row.get("finished_at"),
            )

    async def find_active_repository_sync_job(self, repository_id: UUID) -> Job | None:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                """
                SELECT * FROM ingestion_jobs
                WHERE job_type = 'sync_repository'
                  AND payload->>'repository_id' = %s
                  AND status IN ('pending', 'processing')
                LIMIT 1
                """,
                (str(repository_id),),
            )
            row = await cur.fetchone()
            if not row:
                return None

            return self._row_to_entity(row)

    async def list_by_correlation_id(self, correlation_id: UUID) -> list[Job]:
        async with (
            self._pool.connection() as conn,
            conn.cursor(row_factory=dict_row) as cur,
        ):
            await cur.execute(
                "SELECT * FROM ingestion_jobs WHERE correlation_id = %s",
                (str(correlation_id),),
            )
            rows = await cur.fetchall()
            return [self._row_to_entity(row) for row in rows]

    def _row_to_entity(self, row: dict) -> Job:
        return Job(
            id=UUID(str(row["id"])),
            queue_name=str(row["queue_name"]),
            job_type=str(row["job_type"]),
            payload=row["payload"]
            if isinstance(row["payload"], dict)
            else json.loads(row["payload"]),
            status=JobStatus(str(row["status"])),
            attempts=int(row["attempts"]),
            max_attempts=int(row["max_attempts"]),
            run_at=row["run_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            priority=int(row["priority"]),
            correlation_id=UUID(str(row["correlation_id"]))
            if row.get("correlation_id")
            else None,
            locked_at=row.get("locked_at"),
            locked_by=row.get("locked_by"),
            last_error=row.get("last_error"),
            started_at=row.get("started_at"),
            finished_at=row.get("finished_at"),
        )
