from typing import Protocol
from uuid import UUID

from app.tools.domain.models import RepositorySnapshotRange


class RepositorySnapshotResolverProto(Protocol):
    async def resolve(self, repository_id: UUID) -> RepositorySnapshotRange:
        """
        Locates the latest completed snapshot for the given repository.
        Returns the snapshot range containing paths and IDs.
        Raises RepositoryNotFoundError or RepositorySnapshotNotFoundError.
        """
        ...
