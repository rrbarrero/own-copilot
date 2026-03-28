from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.factory import create_request_repository_sync
from app.repositories.application.request_repository_sync import RequestRepositorySync
from app.repositories.infra.dtos import (
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
