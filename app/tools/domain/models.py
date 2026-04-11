from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


@dataclass(frozen=True)
class FileMatch:
    path: str
    filename: str
    extension: str
    size_bytes: int


@dataclass(frozen=True)
class SearchMatch:
    path: str
    line_number: int
    line_content: str
    start_column: int | None = None


@dataclass(frozen=True)
class RepositorySnapshotRange:
    repository_id: UUID
    sync_id: UUID
    root_path: str


class DiffChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass(frozen=True)
class RepositoryFileDiff:
    path: str
    change_type: DiffChangeType
    unified_diff: str
    additions: int
    deletions: int
    is_binary: bool = False


@dataclass(frozen=True)
class RepositoryDiffResult:
    repository_id: UUID
    base_sync_id: UUID
    head_sync_id: UUID
    file_diffs: list[RepositoryFileDiff]
