from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class RepositorySyncStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RepositorySync:
    id: UUID
    repository_id: UUID
    branch: str
    status: RepositorySyncStatus
    started_at: datetime
    created_at: datetime
    updated_at: datetime
    commit_sha: str | None = None
    finished_at: datetime | None = None
    last_error: str | None = None
    scanned_files: int = 0
    changed_files: int = 0
    deleted_files: int = 0
