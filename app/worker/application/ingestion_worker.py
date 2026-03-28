import asyncio
import logging
import os
import socket
from datetime import UTC, datetime

from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.domain.job_repo_proto import JobRepoProto
from app.worker.application.job_handler_proto import JobHandlerProto

logger = logging.getLogger(__name__)


class IngestionWorker:
    def __init__(
        self,
        job_repo: JobRepoProto,
        handlers: dict[str, JobHandlerProto],
        queue_name: str = "ingestion",
    ):
        self.job_repo = job_repo
        self.handlers = handlers
        self.queue_name = queue_name
        self.worker_id = f"worker-{socket.gethostname()}-{os.getpid()}"
        self._shutdown = False

    async def run(self) -> None:
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

    def stop(self) -> None:
        self._shutdown = True

    async def _process_job(self, job: Job) -> None:
        logger.info(f"[{self.worker_id}] Processing job {job.id} type {job.job_type}")

        handler = self.handlers.get(job.job_type)
        if not handler:
            error_msg = f"No handler registered for job type: {job.job_type}"
            logger.error(f"[{self.worker_id}] {error_msg}")
            job.status = JobStatus.FAILED
            job.last_error = error_msg
            job.finished_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
            await self.job_repo.save(job)
            return

        try:
            # 1. Update job to processing status
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now(UTC)
            job.updated_at = datetime.now(UTC)
            await self.job_repo.save(job)

            # 2. Run handler
            await handler.handle(job)

            # 3. Mark as completed
            job.status = JobStatus.COMPLETED
            logger.info(f"[{self.worker_id}] Job {job.id} completed")

        except Exception as e:
            logger.error(f"[{self.worker_id}] Job {job.id} failed: {e}")
            job.status = JobStatus.FAILED
            job.last_error = str(e)

        # 4. Finalize job status
        job.finished_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        await self.job_repo.save(job)
