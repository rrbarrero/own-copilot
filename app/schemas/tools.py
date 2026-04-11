from uuid import UUID

from pydantic import BaseModel, Field


class FindFilesRequest(BaseModel):
    repository_id: UUID
    repository_sync_id: UUID | None = None
    path_prefix: str | None = None
    query: str | None = None
    extensions: list[str] | None = None
    limit: int = Field(default=50, ge=1, le=100)


class FileMatchSchema(BaseModel):
    path: str
    filename: str
    extension: str
    size_bytes: int


class FindFilesResponse(BaseModel):
    repository_id: UUID
    sync_id: UUID
    files: list[FileMatchSchema]


class ReadFileRequest(BaseModel):
    repository_id: UUID
    repository_sync_id: UUID | None = None
    path: str
    max_chars: int = Field(default=20000, ge=1, le=100000)


class ReadFileResponse(BaseModel):
    repository_id: UUID
    sync_id: UUID
    path: str
    content: str
    size_bytes: int
    truncated: bool


class SearchInRepoRequest(BaseModel):
    repository_id: UUID
    repository_sync_id: UUID | None = None
    query: str
    path_prefix: str | None = None
    extensions: list[str] | None = None
    case_sensitive: bool = False
    limit: int = Field(default=50, ge=1, le=100)


class SearchMatchSchema(BaseModel):
    path: str
    line_number: int
    line_content: str
    start_column: int | None = None


class SearchInRepoResponse(BaseModel):
    repository_id: UUID
    sync_id: UUID
    matches: list[SearchMatchSchema]
