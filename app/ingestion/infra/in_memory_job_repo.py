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
        pending_jobs = [
            j
            for j in self._jobs.values()
            if j.queue_name == queue_name and j.status == JobStatus.PENDING
        ]
        if not pending_jobs:
            return None

        # Sort by priority desc, created_at asc
        pending_jobs.sort(key=lambda x: (-x.priority, x.created_at))
        job = pending_jobs[0]
        job.status = JobStatus.PROCESSING
        job.locked_by = locked_by
        job.attempts += 1
        return job
