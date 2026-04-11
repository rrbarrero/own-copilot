from dataclasses import dataclass
from uuid import UUID

from app.repositories.domain.repository_sync_repo_proto import RepositorySyncRepoProto


@dataclass(frozen=True)
class ResolveRepositoryBranchSyncResult:
    repository_id: UUID
    branch: str
    repository_sync_id: UUID
    commit_sha: str | None


class ResolveRepositoryBranchSync:
    def __init__(self, sync_repo: RepositorySyncRepoProto):
        self._sync_repo = sync_repo

    async def execute(
        self,
        repository_id: UUID,
        branch: str,
    ) -> ResolveRepositoryBranchSyncResult:
        normalized_branch = branch.strip()
        if not normalized_branch:
            raise ValueError("Branch is required.")

        sync = await self._sync_repo.get_latest_completed_by_repository_and_branch(
            repository_id, normalized_branch
        )
        if sync is None:
            raise LookupError(
                "No completed sync found for repository "
                f"{repository_id} on branch {normalized_branch}."
            )

        return ResolveRepositoryBranchSyncResult(
            repository_id=repository_id,
            branch=normalized_branch,
            repository_sync_id=sync.id,
            commit_sha=sync.commit_sha,
        )
