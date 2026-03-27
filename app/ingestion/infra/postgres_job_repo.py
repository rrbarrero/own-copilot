import json
from typing import Any, cast
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
        async with self._pool.connection() as conn, conn.cursor() as cur:
            conn.row_factory = cast(Any, dict_row)
            await cur.execute(
                "SELECT * FROM ingestion_jobs WHERE id = %s", (str(job_id),)
            )
            row = await cur.fetchone()
            if not row:
                return None

            res = cast(dict[str, Any], row)

            return Job(
                id=UUID(str(res["id"])),
                queue_name=str(res["queue_name"]),
                job_type=str(res["job_type"]),
                payload=res["payload"]
                if isinstance(res["payload"], dict)
                else json.loads(res["payload"]),
                status=JobStatus(str(res["status"])),
                attempts=int(res["attempts"]),
                max_attempts=int(res["max_attempts"]),
                run_at=res["run_at"],
                created_at=res["created_at"],
                updated_at=res["updated_at"],
                priority=int(res["priority"]),
                correlation_id=UUID(str(res["correlation_id"]))
                if res.get("correlation_id")
                else None,
                locked_at=res.get("locked_at"),
                locked_by=res.get("locked_by"),
                last_error=res.get("last_error"),
                started_at=res.get("started_at"),
                finished_at=res.get("finished_at"),
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
        async with self._pool.connection() as conn, conn.cursor() as cur:
            conn.row_factory = cast(Any, dict_row)
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

            res = cast(dict[str, Any], row)
            return Job(
                id=UUID(str(res["id"])),
                queue_name=str(res["queue_name"]),
                job_type=str(res["job_type"]),
                payload=res["payload"],
                status=JobStatus(str(res["status"])),
                attempts=int(res["attempts"]),
                max_attempts=int(res["max_attempts"]),
                run_at=res["run_at"],
                created_at=res["created_at"],
                updated_at=res["updated_at"],
                priority=int(res["priority"]),
                correlation_id=UUID(str(res["correlation_id"]))
                if res.get("correlation_id")
                else None,
                locked_at=res.get("locked_at"),
                locked_by=res.get("locked_by"),
                last_error=res.get("last_error"),
                started_at=res.get("started_at"),
                finished_at=res.get("finished_at"),
            )
