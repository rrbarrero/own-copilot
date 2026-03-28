from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Repository:
    id: UUID
    provider: str
    clone_url: str
    normalized_clone_url: str
    owner: str
    name: str
    local_path: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    default_branch: str | None = None
    last_synced_at: datetime | None = None
