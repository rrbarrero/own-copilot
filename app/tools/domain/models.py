from dataclasses import dataclass
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
