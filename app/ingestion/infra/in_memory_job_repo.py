from datetime import UTC, datetime
from uuid import UUID

from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.domain.job_repo_proto import JobRepoProto


class InMemoryJobRepo(JobRepoProto):
    def __init__(self):
        self._jobs: dict[UUID, Job] = {}

    async def save(self, job: Job) -> None:
        self._jobs[job.id] = job

    async def get_by_id(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)

    async def claim_next_job(self, queue_name: str, locked_by: str) -> Job | None:
        now = datetime.now(UTC)
        pending_jobs = [
            j
            for j in self._jobs.values()
            if j.queue_name == queue_name
            and j.status == JobStatus.PENDING
            and j.run_at <= now
            and j.attempts < j.max_attempts
        ]
        if not pending_jobs:
            return None

        # Sort by priority desc, created_at asc
        pending_jobs.sort(key=lambda x: (-x.priority, x.created_at))
        job = pending_jobs[0]

        # Update metadata to reflect the claim (matching Postgres behavior)
        job.status = JobStatus.PROCESSING
        job.locked_by = locked_by
        job.locked_at = now
        job.updated_at = now
        job.attempts += 1

        return job

    async def find_active_repository_sync_job(self, repository_id: UUID) -> Job | None:
        for job in self._jobs.values():
            if (
                job.job_type == "sync_repository"
                and job.payload.get("repository_id") == str(repository_id)
                and job.status in (JobStatus.PENDING, JobStatus.PROCESSING)
            ):
                return job
        return None

    async def list_by_correlation_id(self, correlation_id: UUID) -> list[Job]:
        # Correlation ID is stored in metadata/payload depending on job type.
        # For mock purposes, we'll check common places.
        return [
            j
            for j in self._jobs.values()
            if j.id == correlation_id
            or j.payload.get("correlation_id") == str(correlation_id)
        ]

    async def wait_for_job(self, queue_name: str, timeout: float) -> None:
        """In-memory: just waits or returns if job already exists."""
        # For tests, we might want to actually wait or just return.
        # Given tests use this for mocks, we can just return.
        pass

    async def notify_new_job(self, queue_name: str) -> None:
        """In-memory: noop."""
        pass
