from uuid import UUID

from pydantic import BaseModel, Field


class RepositorySyncRequestDTO(BaseModel):
    clone_url: str = Field(..., description="GitHub clone URL")
    branch: str | None = Field(None, description="Repository branch to sync")


class RepositorySyncResponseDTO(BaseModel):
    repository_id: UUID
    job_id: UUID
    status: str
