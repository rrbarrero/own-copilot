from uuid import UUID

from app.ingestion.domain.job import Job
from app.ingestion.domain.job_repo_proto import JobRepoProto


class InMemoryJobRepo(JobRepoProto):
    def __init__(self):
        self._jobs: dict[UUID, Job] = {}

    async def save(self, job: Job) -> None:
        self._jobs[job.id] = job

    async def get_by_id(self, job_id: UUID) -> Job | None:
        return self._jobs.get(job_id)
