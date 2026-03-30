import os
import shutil
import tempfile
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.tools.application.search_in_repo import SearchInRepo
from app.tools.domain.models import RepositorySnapshotRange


class TestSearchInRepo:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.test_dir = tempfile.mkdtemp()
        self.file1 = "file1.py"
        self.file2 = "file2.txt"
        file1_abs = os.path.join(self.test_dir, self.file1)
        with open(file1_abs, "w", encoding="utf-8") as f:
            f.write("import os\ndef test():\n    return 'import symbol'\n")
        file2_abs = os.path.join(self.test_dir, self.file2)
        with open(file2_abs, "w", encoding="utf-8") as f:
            f.write("Line with IMPORT case\nAnother line\n")

        self.mock_resolver = AsyncMock()
        self.repository_id = uuid4()
        self.sync_id = uuid4()
        self.mock_resolver.resolve.return_value = RepositorySnapshotRange(
            repository_id=self.repository_id,
            sync_id=self.sync_id,
            root_path=self.test_dir,
        )
        self.tool = SearchInRepo(self.mock_resolver)
        yield
        shutil.rmtree(self.test_dir)

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self):
        matches = await self.tool.execute(self.repository_id, query="import")
        assert len(matches) == 3
        assert matches[0].path == self.file1
        assert matches[0].line_number == 1
        assert matches[2].path == self.file2
        assert matches[2].line_number == 1

    @pytest.mark.asyncio
    async def test_case_sensitive_search(self):
        matches = await self.tool.execute(
            self.repository_id, query="IMPORT", case_sensitive=True
        )
        assert len(matches) == 1
        assert matches[0].path == self.file2

    @pytest.mark.asyncio
    async def test_filter_by_extension(self):
        matches = await self.tool.execute(
            self.repository_id, query="import", extensions=["py"]
        )
        assert len(matches) == 2
        for m in matches:
            assert m.path.endswith(".py")

    @pytest.mark.asyncio
    async def test_respect_limit(self):
        matches = await self.tool.execute(self.repository_id, query="import", limit=1)
        assert len(matches) == 1
