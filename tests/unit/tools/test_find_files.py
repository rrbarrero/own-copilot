import os
import shutil
import tempfile
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.tools.application.find_files import FindFiles
from app.tools.domain.models import RepositorySnapshotRange


class TestFindFiles:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        # Create some dummy files
        os.makedirs(os.path.join(self.test_dir, "subdir"))
        file1 = os.path.join(self.test_dir, "file1.py")
        open(file1, "a").close()
        file2 = os.path.join(self.test_dir, "file2.txt")
        open(file2, "a").close()
        file3 = os.path.join(self.test_dir, "subdir", "file3.py")
        open(file3, "a").close()

        self.mock_resolver = AsyncMock()
        self.repository_id = uuid4()
        self.sync_id = uuid4()
        self.mock_resolver.resolve.return_value = RepositorySnapshotRange(
            repository_id=self.repository_id,
            sync_id=self.sync_id,
            root_path=self.test_dir,
        )
        self.tool = FindFiles(self.mock_resolver)
        yield
        shutil.rmtree(self.test_dir)

    @pytest.mark.asyncio
    async def test_find_all_files(self):
        matches = await self.tool.execute(self.repository_id)
        assert len(matches) == 3
        assert matches[0].path == "file1.py"
        assert matches[1].path == "file2.txt"
        assert matches[2].path == "subdir/file3.py"

    @pytest.mark.asyncio
    async def test_filter_by_extension(self):
        matches = await self.tool.execute(self.repository_id, extensions=["py"])
        assert len(matches) == 2
        for m in matches:
            assert m.extension == "py"

    @pytest.mark.asyncio
    async def test_filter_by_query(self):
        matches = await self.tool.execute(self.repository_id, query="file3")
        assert len(matches) == 1
        assert matches[0].filename == "file3.py"

    @pytest.mark.asyncio
    async def test_respect_limit(self):
        matches = await self.tool.execute(self.repository_id, limit=1)
        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_uses_explicit_repository_sync_id(self):
        explicit_sync_id = uuid4()

        await self.tool.execute(
            self.repository_id,
            repository_sync_id=explicit_sync_id,
        )

        self.mock_resolver.resolve.assert_awaited_with(
            self.repository_id,
            explicit_sync_id,
        )
