from typing import Protocol
from uuid import UUID

from app.tools.domain.models import RepositorySnapshotRange


class RepositorySnapshotResolverProto(Protocol):
    async def resolve(
        self,
        repository_id: UUID,
        repository_sync_id: UUID | None = None,
    ) -> RepositorySnapshotRange:
        """
        Locates a concrete snapshot for the given repository.
        If repository_sync_id is not provided, resolves the latest completed snapshot.
        Returns the snapshot range containing paths and IDs.
        Raises RepositoryNotFoundError or RepositorySnapshotNotFoundError.
        """
        ...
