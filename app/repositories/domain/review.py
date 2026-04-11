from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class ReviewFinding:
    severity: Literal["low", "medium", "high"]
    path: str
    title: str
    rationale: str
    line_start: int | None = None
    line_end: int | None = None


@dataclass(frozen=True)
class RepositoryBranchReview:
    repository_id: UUID
    base_branch: str
    branch: str
    base_sync_id: UUID
    head_sync_id: UUID
    summary: str
    findings: list[ReviewFinding]
