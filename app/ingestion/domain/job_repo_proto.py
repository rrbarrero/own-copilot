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
