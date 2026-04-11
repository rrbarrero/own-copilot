from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.factory import (
    create_request_repository_sync,
    create_resolve_repository_branch_sync,
    create_review_repository_branch_against_main,
)
from app.repositories.application.request_repository_sync import RequestRepositorySync
from app.repositories.application.resolve_repository_branch_sync import (
    ResolveRepositoryBranchSync,
)
from app.repositories.application.review_repository_branch_against_main import (
    ReviewRepositoryBranchAgainstMain,
)
from app.repositories.infra.dtos import (
    RepositoryBranchSyncResolveRequestDTO,
    RepositoryBranchSyncResolveResponseDTO,
    RepositoryReviewFindingDTO,
    RepositoryReviewRequestDTO,
    RepositoryReviewResponseDTO,
    RepositorySyncRequestDTO,
    RepositorySyncResponseDTO,
)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("/sync", response_model=RepositorySyncResponseDTO)
async def request_sync(
    request: RepositorySyncRequestDTO,
    service: Annotated[RequestRepositorySync, Depends(create_request_repository_sync)],
) -> RepositorySyncResponseDTO:
    """
    Enqueues a repository synchronization task.
    """
    try:
        result = await service.execute(
            clone_url=request.clone_url,
            branch=request.branch,
        )
        return RepositorySyncResponseDTO(
            repository_id=result.repository_id,
            job_id=result.job_id,
            status=result.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") from e


@router.post("/resolve-branch", response_model=RepositoryBranchSyncResolveResponseDTO)
async def resolve_branch(
    request: RepositoryBranchSyncResolveRequestDTO,
    service: Annotated[
        ResolveRepositoryBranchSync,
        Depends(create_resolve_repository_branch_sync),
    ],
) -> RepositoryBranchSyncResolveResponseDTO:
    try:
        result = await service.execute(
            repository_id=request.repository_id,
            branch=request.branch,
        )
        return RepositoryBranchSyncResolveResponseDTO(
            repository_id=result.repository_id,
            branch=result.branch,
            repository_sync_id=result.repository_sync_id,
            commit_sha=result.commit_sha,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") from e


@router.post("/review", response_model=RepositoryReviewResponseDTO)
async def review_branch(
    request: RepositoryReviewRequestDTO,
    service: Annotated[
        ReviewRepositoryBranchAgainstMain,
        Depends(create_review_repository_branch_against_main),
    ],
) -> RepositoryReviewResponseDTO:
    try:
        result = await service.execute(
            repository_id=request.repository_id,
            branch=request.branch,
        )
        return RepositoryReviewResponseDTO(
            repository_id=result.repository_id,
            base_branch=result.base_branch,
            branch=result.branch,
            base_sync_id=result.base_sync_id,
            head_sync_id=result.head_sync_id,
            summary=result.summary,
            findings=[
                RepositoryReviewFindingDTO(
                    severity=finding.severity,
                    path=finding.path,
                    title=finding.title,
                    rationale=finding.rationale,
                    line_start=finding.line_start,
                    line_end=finding.line_end,
                )
                for finding in result.findings
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") from e
