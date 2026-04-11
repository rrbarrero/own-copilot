import os
import shutil
import tempfile
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.tools.application.read_file import ReadFile
from app.tools.domain.errors import (
    InvalidRepositoryPathError,
    RepositoryFileNotFoundError,
)
from app.tools.domain.models import RepositorySnapshotRange


class TestReadFile:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.file_path = "test.py"
        self.abs_path = os.path.join(self.test_dir, self.file_path)
        with open(self.abs_path, "w", encoding="utf-8") as f:
            f.write("print('hello')\nline2\nline3")

        self.mock_resolver = AsyncMock()
        self.repository_id = uuid4()
        self.sync_id = uuid4()
        self.mock_resolver.resolve.return_value = RepositorySnapshotRange(
            repository_id=self.repository_id,
            sync_id=self.sync_id,
            root_path=self.test_dir,
        )
        self.tool = ReadFile(self.mock_resolver)
        yield
        shutil.rmtree(self.test_dir)

    @pytest.mark.asyncio
    async def test_read_success(self):
        result = await self.tool.execute(self.repository_id, self.file_path)
        assert result.content == "print('hello')\nline2\nline3"
        assert not result.truncated

    @pytest.mark.asyncio
    async def test_read_truncated(self):
        result = await self.tool.execute(
            self.repository_id, self.file_path, max_chars=5
        )
        assert result.content == "print"
        assert result.truncated

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        with pytest.raises(RepositoryFileNotFoundError):
            await self.tool.execute(self.repository_id, "non-existent.py")

    @pytest.mark.asyncio
    async def test_prevent_path_traversal(self):
        with pytest.raises(InvalidRepositoryPathError):
            await self.tool.execute(self.repository_id, "../outside.py")

    @pytest.mark.asyncio
    async def test_uses_explicit_repository_sync_id(self):
        explicit_sync_id = uuid4()

        await self.tool.execute(
            self.repository_id,
            repository_sync_id=explicit_sync_id,
            path=self.file_path,
        )

        self.mock_resolver.resolve.assert_awaited_with(
            self.repository_id,
            explicit_sync_id,
        )
