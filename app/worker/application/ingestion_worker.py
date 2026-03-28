import asyncio
import logging
import os
import socket
from datetime import UTC, datetime

from app.ingestion.domain.document import ProcessingStatus
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.domain.job_repo_proto import JobRepoProto
from app.worker.application.pipeline import Pipeline
from app.worker.domain.pipeline_context import PipelineContext

logger = logging.getLogger(__name__)


class IngestionWorker:
    def __init__(
        self,
        job_repo: JobRepoProto,
        document_repo: DocumentRepoProto,
        pipeline: Pipeline,
        queue_name: str = "ingestion",
    ):
        self.job_repo = job_repo
        self.document_repo = document_repo
        self.pipeline = pipeline
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

        # Map doc_uuid from the payload to document_id in the context
        document_id = job.payload.get("doc_uuid")

        # 1. Initialize PipelineContext with job data
        ctx = PipelineContext(
            job_id=str(job.id),
            job_type=job.job_type,
            payload=job.payload,
            document_id=document_id,
        )

        # 2. Update document status to PROCESSING
        doc = None
        if document_id:
            doc = await self.document_repo.get_by_uuid(document_id)
            if doc:
                doc.processing_status = ProcessingStatus.PROCESSING
                doc.updated_at = datetime.now(UTC)
                await self.document_repo.save(doc)

        try:
            # 3. Run the pipeline
            await self.pipeline.run(ctx)

            # 4. Mark as completed
            if doc:
                doc.processing_status = ProcessingStatus.INDEXED
                doc.indexed_at = datetime.now(UTC)
                doc.updated_at = datetime.now(UTC)
                await self.document_repo.save(doc)

            job.status = JobStatus.COMPLETED
            logger.info(f"[{self.worker_id}] Job {job.id} completed")

        except Exception as e:
            logger.error(f"[{self.worker_id}] Job {job.id} failed: {e}")
            if doc:
                doc.processing_status = ProcessingStatus.FAILED
                doc.last_error = str(e)
                doc.updated_at = datetime.now(UTC)
                await self.document_repo.save(doc)

            job.status = JobStatus.FAILED
            job.last_error = str(e)

        # 5. Finalize job status
        job.finished_at = datetime.now(UTC)
        job.updated_at = datetime.now(UTC)
        await self.job_repo.save(job)
