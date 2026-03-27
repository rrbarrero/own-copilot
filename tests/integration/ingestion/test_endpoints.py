import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.factory import create_ingestion_service
from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.infra.in_memory_document_repo import InMemoryDocumentRepo
from app.ingestion.infra.in_memory_job_repo import InMemoryJobRepo
from app.ingestion.infra.in_memory_storage_repo import InMemoryStorageRepo

# Reusable in-memory repos for tests
doc_repo = InMemoryDocumentRepo()
storage_repo = InMemoryStorageRepo()
job_repo = InMemoryJobRepo()


def override_create_ingestion_service():
    return IngestionService(
        doc_repo=doc_repo, storage_repo=storage_repo, job_repo=job_repo
    )


# Override dependency
app.dependency_overrides[create_ingestion_service] = override_create_ingestion_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_repos():
    # Clear in-memory storage before each test
    doc_repo._documents = {}
    storage_repo._storage = {}
    job_repo._jobs = {}


def test_upload_file_endpoint_success():
    # Given
    file_content = b"Content for testing endpoint"
    filename = "test.txt"
    files = [("files", (filename, file_content, "text/plain"))]
    headers = {"X-Idempotency-Key": str(uuid.uuid4())}

    # When
    response = client.post("/ingestion/upload", files=files, headers=headers)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == filename
    doc_uuid = data[0]["uuid"]

    # Verify persistence
    assert doc_uuid in [str(u) for u in doc_repo._documents]
    assert len(job_repo._jobs) == 1


def test_upload_multiple_files_success():
    # Given
    files = [
        ("files", ("test1.txt", b"content1", "text/plain")),
        ("files", ("test2.txt", b"content2", "text/plain")),
    ]
    headers = {"X-Idempotency-Key": str(uuid.uuid4())}

    # When
    response = client.post("/ingestion/upload", files=files, headers=headers)

    # Then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["filename"] == "test1.txt"
    assert data[1]["filename"] == "test2.txt"

    # Verify persistence
    assert len(doc_repo._documents) == 2
    assert len(job_repo._jobs) == 2


def test_upload_too_many_files_fails():
    # Given (more than 10 files)
    files = [("files", (f"test{i}.txt", b"content", "text/plain")) for i in range(11)]
    headers = {"X-Idempotency-Key": str(uuid.uuid4())}

    # When
    response = client.post("/ingestion/upload", files=files, headers=headers)

    # Then
    assert response.status_code == 400
    assert "Maximum 10 files allowed." in response.json()["detail"]


def test_upload_invalid_extension_fails():
    # Given (.exe is not allowed)
    files = [("files", ("evil.exe", b"malware content", "application/octet-stream"))]
    headers = {"X-Idempotency-Key": str(uuid.uuid4())}

    # When
    response = client.post("/ingestion/upload", files=files, headers=headers)

    # Then
    assert response.status_code == 400
    assert "not allowed. Allowed:" in response.json()["detail"]


def test_upload_file_too_large_fails():
    # Given (more than 1MB)
    large_content = b"a" * (1024 * 1024 + 1)
    files = [("files", ("large.txt", large_content, "text/plain"))]
    headers = {"X-Idempotency-Key": str(uuid.uuid4())}

    # When
    response = client.post("/ingestion/upload", files=files, headers=headers)

    # Then
    assert response.status_code == 400
    assert "exceeds 1MB limit." in response.json()["detail"]


def test_upload_file_idempotency_success():
    # Given
    file_content = b"Content for testing idempotency"
    filename = "idempotent.txt"
    files = [("files", (filename, file_content, "text/plain"))]
    idempotency_key = str(uuid.uuid4())
    headers = {"X-Idempotency-Key": idempotency_key}

    # When: Initial request
    response1 = client.post("/ingestion/upload", files=files, headers=headers)
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1[0]["filename"] == filename

    # When: Duplicate request with same key
    response2 = client.post("/ingestion/upload", files=files, headers=headers)

    # Then
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2[0]["uuid"] == data1[0]["uuid"]
    assert data2[0]["status"] == "already_processed"
    assert len(doc_repo._documents) == 1
    assert len(job_repo._jobs) == 1


def test_upload_without_idempotency_fails():
    # When
    response = client.post("/ingestion/upload", files=[])

    # Then
    assert response.status_code == 422  # Validation Error
    assert "X-Idempotency-Key" in response.text
