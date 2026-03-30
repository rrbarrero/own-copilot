from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.factory import (
    create_repository_snapshot_resolver,
    create_repository_tool_service,
)
from app.schemas.tools import (
    FileMatchSchema,
    FindFilesRequest,
    FindFilesResponse,
    ReadFileRequest,
    ReadFileResponse,
    SearchInRepoRequest,
    SearchInRepoResponse,
    SearchMatchSchema,
)
from app.tools.application.repository_tool_service import RepositoryToolService
from app.tools.domain.errors import ToolError
from app.tools.domain.repository_snapshot_resolver_proto import (
    RepositorySnapshotResolverProto,
)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/find-files", response_model=FindFilesResponse)
async def find_files(
    request: FindFilesRequest,
    tool_service: Annotated[
        RepositoryToolService, Depends(create_repository_tool_service)
    ],
    resolver: Annotated[
        RepositorySnapshotResolverProto, Depends(create_repository_snapshot_resolver)
    ],
):
    try:
        # Resolve snapshot to get metadata (sync_id)
        snapshot = await resolver.resolve(request.repository_id)

        files = await tool_service.find_files(
            repository_id=request.repository_id,
            path_prefix=request.path_prefix,
            query=request.query,
            extensions=request.extensions,
            limit=request.limit,
        )

        return FindFilesResponse(
            repository_id=snapshot.repository_id,
            sync_id=snapshot.sync_id,
            files=[FileMatchSchema(**f.__dict__) for f in files],
        )
    except ToolError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/read-file", response_model=ReadFileResponse)
async def read_file(
    request: ReadFileRequest,
    tool_service: Annotated[
        RepositoryToolService, Depends(create_repository_tool_service)
    ],
):
    try:
        result = await tool_service.read_file(
            repository_id=request.repository_id,
            path=request.path,
            max_chars=request.max_chars,
        )

        return ReadFileResponse(
            repository_id=result.repository_id,
            sync_id=result.sync_id,
            path=result.path,
            content=result.content,
            size_bytes=result.size_bytes,
            truncated=result.truncated,
        )
    except ToolError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/search-in-repo", response_model=SearchInRepoResponse)
async def search_in_repo(
    request: SearchInRepoRequest,
    tool_service: Annotated[
        RepositoryToolService, Depends(create_repository_tool_service)
    ],
    resolver: Annotated[
        RepositorySnapshotResolverProto, Depends(create_repository_snapshot_resolver)
    ],
):
    try:
        # Resolve snapshot to get metadata
        snapshot = await resolver.resolve(request.repository_id)

        matches = await tool_service.search_in_repo(
            repository_id=request.repository_id,
            query=request.query,
            path_prefix=request.path_prefix,
            extensions=request.extensions,
            case_sensitive=request.case_sensitive,
            limit=request.limit,
        )

        return SearchInRepoResponse(
            repository_id=snapshot.repository_id,
            sync_id=snapshot.sync_id,
            matches=[SearchMatchSchema(**m.__dict__) for m in matches],
        )
    except ToolError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
