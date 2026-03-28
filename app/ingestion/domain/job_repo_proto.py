from typing import Protocol
from uuid import UUID

from app.ingestion.domain.job import Job


class JobRepoProto(Protocol):
    async def save(self, job: Job) -> None:
        """Saves or updates a job in persistence."""
        ...

    async def get_by_id(self, job_id: UUID) -> Job | None:
        """Retrieves a job by its unique identifier."""
        ...

    async def claim_next_job(self, queue_name: str, locked_by: str) -> Job | None:
        """Claims the next pending job using SKIP LOCKED."""
        ...

    async def find_active_repository_sync_job(self, repository_id: UUID) -> Job | None:
        """Finds any currently processing sync job for a repository."""
        ...

    async def list_by_correlation_id(self, correlation_id: UUID) -> list[Job]:
        """Lists all jobs sharing the same correlation identifier."""
        ...
