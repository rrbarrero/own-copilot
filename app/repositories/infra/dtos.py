from uuid import UUID

from pydantic import BaseModel, Field


class RepositorySyncRequestDTO(BaseModel):
    clone_url: str = Field(..., description="GitHub clone URL")
    branch: str | None = Field(None, description="Repository branch to sync")


class RepositorySyncResponseDTO(BaseModel):
    repository_id: UUID
    job_id: UUID
    status: str


class RepositoryReviewRequestDTO(BaseModel):
    repository_id: UUID
    branch: str = Field(..., min_length=1, description="Branch to review")


class RepositoryReviewFindingDTO(BaseModel):
    severity: str
    path: str
    title: str
    rationale: str
    line_start: int | None = None
    line_end: int | None = None


class RepositoryReviewResponseDTO(BaseModel):
    repository_id: UUID
    base_branch: str
    branch: str
    base_sync_id: UUID
    head_sync_id: UUID
    summary: str
    findings: list[RepositoryReviewFindingDTO]


class RepositoryBranchSyncResolveRequestDTO(BaseModel):
    repository_id: UUID
    branch: str = Field(..., min_length=1, description="Branch to resolve")


class RepositoryBranchSyncResolveResponseDTO(BaseModel):
    repository_id: UUID
    branch: str
    repository_sync_id: UUID
    commit_sha: str | None = None
