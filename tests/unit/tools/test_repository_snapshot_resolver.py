import os
import shutil
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.repositories.domain.repository_sync import (
    RepositorySync,
    RepositorySyncStatus,
)
from app.tools.domain.errors import (
    RepositoryNotFoundError,
    RepositorySnapshotNotFoundError,
)
from app.tools.infra.filesystem_repository_snapshot_resolver import (
    FilesystemRepositorySnapshotResolver,
)


class TestRepositorySnapshotResolver:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.repo_id = uuid4()
        self.sync_id = uuid4()

        self.repository_repo = AsyncMock()
        self.sync_repo = AsyncMock()

        self.resolver = FilesystemRepositorySnapshotResolver(
            self.repository_repo, self.sync_repo, self.test_dir
        )
        yield
        shutil.rmtree(self.test_dir)

    @pytest.mark.asyncio
    async def test_resolve_success(self):
        # 1. Setup repo
        self.repository_repo.get_by_id.return_value = MagicMock(id=self.repo_id)

        # 2. Setup syncs
        sync_completed = RepositorySync(
            id=self.sync_id,
            repository_id=self.repo_id,
            branch="main",
            status=RepositorySyncStatus.COMPLETED,
            started_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.sync_repo.list_by_repository_id.return_value = [sync_completed]

        # 3. Create directory
        snapshot_path = os.path.join(
            self.test_dir, f"repositories/{self.repo_id}/{self.sync_id}"
        )
        os.makedirs(snapshot_path)

        # 4. Execute
        result = await self.resolver.resolve(self.repo_id)
        assert result.sync_id == self.sync_id
        assert result.root_path == snapshot_path

    @pytest.mark.asyncio
    async def test_repository_not_found(self):
        self.repository_repo.get_by_id.return_value = None
        with pytest.raises(RepositoryNotFoundError):
            await self.resolver.resolve(self.repo_id)

    @pytest.mark.asyncio
    async def test_no_completed_sync(self):
        self.repository_repo.get_by_id.return_value = MagicMock(id=self.repo_id)
        sync_running = RepositorySync(
            id=self.sync_id,
            repository_id=self.repo_id,
            branch="main",
            status=RepositorySyncStatus.RUNNING,
            started_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.sync_repo.list_by_repository_id.return_value = [sync_running]

        with pytest.raises(RepositorySnapshotNotFoundError):
            await self.resolver.resolve(self.repo_id)

    @pytest.mark.asyncio
    async def test_snapshot_directory_missing(self):
        self.repository_repo.get_by_id.return_value = MagicMock(id=self.repo_id)
        sync_completed = RepositorySync(
            id=self.sync_id,
            repository_id=self.repo_id,
            branch="main",
            status=RepositorySyncStatus.COMPLETED,
            started_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.sync_repo.list_by_repository_id.return_value = [sync_completed]

        # Directory NOT created
        with pytest.raises(RepositorySnapshotNotFoundError):
            await self.resolver.resolve(self.repo_id)

    @pytest.mark.asyncio
    async def test_resolve_specific_sync_success(self):
        self.repository_repo.get_by_id.return_value = MagicMock(id=self.repo_id)
        sync_completed = RepositorySync(
            id=self.sync_id,
            repository_id=self.repo_id,
            branch="feature/test",
            status=RepositorySyncStatus.COMPLETED,
            started_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self.sync_repo.get_by_id.return_value = sync_completed

        snapshot_path = os.path.join(
            self.test_dir, f"repositories/{self.repo_id}/{self.sync_id}"
        )
        os.makedirs(snapshot_path)

        result = await self.resolver.resolve(
            self.repo_id, repository_sync_id=self.sync_id
        )

        assert result.sync_id == self.sync_id
        self.sync_repo.get_by_id.assert_awaited_once_with(self.sync_id)
