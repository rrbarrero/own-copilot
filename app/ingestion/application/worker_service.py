import asyncio
import logging
import os
import socket
from datetime import UTC, datetime

from app.ingestion.domain.job import JobStatus
from app.ingestion.domain.job_repo_proto import JobRepoProto

logger = logging.getLogger(__name__)


class IngestionWorker:
    def __init__(self, job_repo: JobRepoProto, queue_name: str = "ingestion"):
        self.job_repo = job_repo
        self.queue_name = queue_name
        self.worker_id = f"worker-{socket.gethostname()}-{os.getpid()}"
        self._shutdown = False

    async def run(self):
        logger.info(f"Starting worker {self.worker_id} on queue {self.queue_name}")

        while not self._shutdown:
            try:
                job = await self.job_repo.claim_next_job(
                    self.queue_name, self.worker_id
                )
                if job:
                    await self._process_job(job)
                else:
                    # No jobs, sleep a bit
                    await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(5)

    def stop(self):
        self._shutdown = True

    async def _process_job(self, job):
        logger.info(f"[{self.worker_id}] Processing job {job.id} type {job.job_type}")
        print(f"PROCESANDO JOB: {job.id} - {job.job_type} - Payload: {job.payload}")

        # Simulate work
        await asyncio.sleep(1)

        # Mark as completed
        job.status = JobStatus.COMPLETED
        job.finished_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        await self.job_repo.save(job)
        logger.info(f"[{self.worker_id}] Job {job.id} completed")
