from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID


class JobStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    id: UUID
    queue_name: str
    job_type: str
    payload: dict[str, Any]
    status: JobStatus
    attempts: int
    max_attempts: int
    run_at: datetime
    created_at: datetime
    updated_at: datetime
    priority: int = 0
    correlation_id: UUID | None = None
    locked_at: datetime | None = None
    locked_by: str | None = None
    last_error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
