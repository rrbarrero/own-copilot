import os
from uuid import UUID

from app.repositories.domain.repository_repo_proto import RepositoryRepoProto
from app.repositories.domain.repository_sync import RepositorySyncStatus
from app.repositories.domain.repository_sync_repo_proto import RepositorySyncRepoProto
from app.tools.domain.errors import (
    RepositoryNotFoundError,
    RepositorySnapshotNotFoundError,
)
from app.tools.domain.models import RepositorySnapshotRange


class FilesystemRepositorySnapshotResolver:
    def __init__(
        self,
        repository_repo: RepositoryRepoProto,
        sync_repo: RepositorySyncRepoProto,
        storage_path: str,
    ):
        self._repository_repo = repository_repo
        self._sync_repo = sync_repo
        self._storage_path = storage_path

    async def resolve(self, repository_id: UUID) -> RepositorySnapshotRange:
        # 1. Verify repository exists
        repo = await self._repository_repo.get_by_id(repository_id)
        if not repo:
            raise RepositoryNotFoundError(repository_id)

        # 2. Find the last COMPLETED sync
        syncs = await self._sync_repo.list_by_repository_id(repository_id)
        last_completed = next(
            (s for s in syncs if s.status == RepositorySyncStatus.COMPLETED), None
        )

        if not last_completed:
            raise RepositorySnapshotNotFoundError(repository_id)

        # 3. Resolve path: storage/repositories/{repository_id}/{sync_id}/
        # Using the same convention as InFilesystemStorageRepo
        snapshot_rel_path = f"repositories/{repository_id}/{last_completed.id}"
        snapshot_abs_path = os.path.join(self._storage_path, snapshot_rel_path)

        # 4. Check if directory exists
        if not os.path.isdir(snapshot_abs_path):
            raise RepositorySnapshotNotFoundError(repository_id)

        return RepositorySnapshotRange(
            repository_id=repository_id,
            sync_id=last_completed.id,
            root_path=snapshot_abs_path,
        )
