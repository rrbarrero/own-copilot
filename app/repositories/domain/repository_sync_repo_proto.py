from typing import Protocol
from uuid import UUID

from app.repositories.domain.repository_sync import RepositorySync


class RepositorySyncRepoProto(Protocol):
    async def save(self, sync: RepositorySync) -> None: ...

    async def get_by_id(self, sync_id: UUID) -> RepositorySync | None: ...

    async def get_running_by_repository_id(
        self, repository_id: UUID
    ) -> RepositorySync | None: ...

    async def get_latest_by_repository_id(
        self, repository_id: UUID
    ) -> RepositorySync | None: ...
