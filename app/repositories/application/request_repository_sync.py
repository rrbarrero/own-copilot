import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.ingestion.domain.job import Job, JobStatus
from app.ingestion.domain.job_repo_proto import JobRepoProto
from app.repositories.domain.repository import Repository
from app.repositories.domain.repository_repo_proto import RepositoryRepoProto
from app.repositories.infra.repository_url_normalizer import RepositoryUrlNormalizer


@dataclass
class RequestRepositorySyncResult:
    repository_id: UUID
    job_id: UUID
    status: str


class RequestRepositorySync:
    def __init__(
        self,
        repository_repo: RepositoryRepoProto,
        job_repo: JobRepoProto,
        url_normalizer: RepositoryUrlNormalizer,
        checkouts_root: str,
    ):
        self._repository_repo = repository_repo
        self._job_repo = job_repo
        self._url_normalizer = url_normalizer
        self._checkouts_root = checkouts_root

    async def execute(
        self, clone_url: str, branch: str | None = None
    ) -> RequestRepositorySyncResult:
        """
        Request a repository synchronization.
        Normalizes the URL, ensures the repository exists in DB,
        and enqueues a sync job if not already active.
        """
        url_info = self._url_normalizer.normalize(clone_url)

        # 1. Ensure repository exists
        repo = await self._repository_repo.get_by_normalized_url(
            url_info.normalized_url
        )

        if not repo:
            repo = Repository(
                id=uuid.uuid4(),
                provider="github",
                clone_url=clone_url,
                normalized_clone_url=url_info.normalized_url,
                owner=url_info.owner,
                name=url_info.name,
                local_path=f"{self._checkouts_root}/{url_info.owner}_{url_info.name}",
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                default_branch=branch,
            )
            await self._repository_repo.save(repo)

        # 2. Check for active sync jobs for this repository
        active_job = await self._job_repo.find_active_repository_sync_job(repo.id)

        if active_job:
            return RequestRepositorySyncResult(
                repository_id=repo.id,
                job_id=active_job.id,
                status="already_queued",
            )

        # 3. Create new job
        job_id = uuid.uuid4()
        job = Job(
            id=job_id,
            queue_name="ingestion",
            job_type="sync_repository",
            payload={
                "repository_id": str(repo.id),
                "branch": branch or repo.default_branch or "main",
            },
            status=JobStatus.PENDING,
            attempts=0,
            max_attempts=3,
            run_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            priority=10,  # Higher priority for syncs than single docs?
        )
        await self._job_repo.save(job)

        return RequestRepositorySyncResult(
            repository_id=repo.id,
            job_id=job_id,
            status="queued",
        )
