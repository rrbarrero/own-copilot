from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.ingestion.application.worker_service import IngestionWorker
from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.infra.in_memory_job_repo import InMemoryJobRepo
from app.worker.application.pipeline import Pipeline
from app.worker.domain.pipeline_context import PipelineContext


class FailingPipeline(Pipeline):
    def __init__(self, error_message: str):
        super().__init__(steps=[])
        self.error_message = error_message

    async def run(self, ctx: PipelineContext) -> None:  # noqa: ARG002
        raise Exception(self.error_message)


@pytest.mark.asyncio
async def test_worker_persists_last_error_on_failure():
    # 1. Setup
    job_repo = InMemoryJobRepo()
    error_msg = "Critical error during pipeline execution"
    pipeline = FailingPipeline(error_msg)
    worker = IngestionWorker(job_repo=job_repo, pipeline=pipeline)

    job_id = uuid4()
    job = Job(
        id=job_id,
        queue_name="ingestion",
        job_type="test",
        payload={"foo": "bar"},
        status=JobStatus.PENDING,
        attempts=0,
        max_attempts=3,
        run_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await job_repo.save(job)

    # 2. Execute process_job
    # This should mark the job as FAILED and save the error message
    await worker._process_job(job)

    # 3. Assertions on the object
    assert job.status == JobStatus.FAILED
    assert job.last_error == error_msg
    assert job.finished_at is not None

    # 4. Verify persistence in the repo
    saved_job = await job_repo.get_by_id(job_id)
    assert saved_job is not None
    assert saved_job.status == JobStatus.FAILED
    assert saved_job.last_error == error_msg
