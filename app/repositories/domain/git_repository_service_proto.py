from dataclasses import dataclass
from typing import Protocol

from app.repositories.domain.repository import Repository


@dataclass
class CheckoutInfo:
    local_path: str
    branch: str
    commit_sha: str


class GitRepositoryServiceProto(Protocol):
    async def ensure_checkout(
        self, repository: Repository, branch: str | None = None
    ) -> CheckoutInfo:
        """Ensures a local clone/checkout exists and is at the correct version."""
        ...
