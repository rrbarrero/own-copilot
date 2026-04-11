from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.main import app
from app.factory import create_resolve_repository_branch_sync
from app.factory import create_review_repository_branch_against_main
from app.repositories.domain.review import RepositoryBranchReview, ReviewFinding


def test_review_repository_endpoint_success():
    service = AsyncMock()
    service.execute.return_value = RepositoryBranchReview(
        repository_id=uuid4(),
        base_branch="main",
        branch="feature/review-me",
        base_sync_id=uuid4(),
        head_sync_id=uuid4(),
        summary="One review finding.",
        findings=[
            ReviewFinding(
                severity="medium",
                path="app/example.py",
                title="Potential issue",
                rationale="Needs a null check.",
                line_start=10,
                line_end=12,
            )
        ],
    )

    app.dependency_overrides[create_review_repository_branch_against_main] = (
        lambda: service
    )
    client = TestClient(app)

    response = client.post(
        "/repositories/review",
        json={
            "repository_id": str(service.execute.return_value.repository_id),
            "branch": "feature/review-me",
        },
    )

    app.dependency_overrides.pop(create_review_repository_branch_against_main, None)

    assert response.status_code == 200
    data = response.json()
    assert data["base_branch"] == "main"
    assert data["branch"] == "feature/review-me"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["path"] == "app/example.py"


def test_resolve_repository_branch_endpoint_success():
    service = AsyncMock()
    repository_id = uuid4()
    repository_sync_id = uuid4()
    service.execute.return_value.repository_id = repository_id
    service.execute.return_value.branch = "feature/review-me"
    service.execute.return_value.repository_sync_id = repository_sync_id
    service.execute.return_value.commit_sha = "abc123"

    app.dependency_overrides[create_resolve_repository_branch_sync] = lambda: service
    client = TestClient(app)

    response = client.post(
        "/repositories/resolve-branch",
        json={
            "repository_id": str(repository_id),
            "branch": "feature/review-me",
        },
    )

    app.dependency_overrides.pop(create_resolve_repository_branch_sync, None)

    assert response.status_code == 200
    data = response.json()
    assert data["repository_id"] == str(repository_id)
    assert data["branch"] == "feature/review-me"
    assert data["repository_sync_id"] == str(repository_sync_id)
    assert data["commit_sha"] == "abc123"
