from typing import Protocol

from app.ingestion.domain.job import Job


class JobHandlerProto(Protocol):
    async def handle(self, job: Job) -> None:
        """Processes a specific type of job."""
        ...
