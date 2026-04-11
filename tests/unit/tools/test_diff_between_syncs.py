from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.tools.application.diff_between_syncs import DiffBetweenSyncs
from app.tools.domain.models import DiffChangeType, RepositorySnapshotRange


class TestDiffBetweenSyncs:
    @pytest.mark.asyncio
    async def test_execute_detects_added_modified_and_deleted_files(self, tmp_path):
        repository_id = uuid4()
        base_sync_id = uuid4()
        head_sync_id = uuid4()

        base_root = tmp_path / "base"
        head_root = tmp_path / "head"
        base_root.mkdir()
        head_root.mkdir()

        (base_root / "changed.py").write_text("value = 1\n", encoding="utf-8")
        (head_root / "changed.py").write_text("value = 2\n", encoding="utf-8")
        (base_root / "deleted.py").write_text("old = True\n", encoding="utf-8")
        (head_root / "added.py").write_text("new = True\n", encoding="utf-8")

        resolver = AsyncMock()
        resolver.resolve.side_effect = [
            RepositorySnapshotRange(
                repository_id=repository_id,
                sync_id=base_sync_id,
                root_path=str(base_root),
            ),
            RepositorySnapshotRange(
                repository_id=repository_id,
                sync_id=head_sync_id,
                root_path=str(head_root),
            ),
        ]

        service = DiffBetweenSyncs(resolver)

        result = await service.execute(repository_id, base_sync_id, head_sync_id)

        assert result.base_sync_id == base_sync_id
        assert result.head_sync_id == head_sync_id
        assert [diff.path for diff in result.file_diffs] == [
            "added.py",
            "changed.py",
            "deleted.py",
        ]

        change_map = {diff.path: diff for diff in result.file_diffs}
        assert change_map["added.py"].change_type == DiffChangeType.ADDED
        assert change_map["changed.py"].change_type == DiffChangeType.MODIFIED
        assert change_map["deleted.py"].change_type == DiffChangeType.DELETED
        assert "+new = True" in change_map["added.py"].unified_diff
        assert "-value = 1" in change_map["changed.py"].unified_diff
        assert "+value = 2" in change_map["changed.py"].unified_diff

    @pytest.mark.asyncio
    async def test_execute_marks_non_utf8_as_binary(self, tmp_path):
        repository_id = uuid4()
        base_sync_id = uuid4()
        head_sync_id = uuid4()

        base_root = tmp_path / "base_bin"
        head_root = tmp_path / "head_bin"
        base_root.mkdir()
        head_root.mkdir()

        (base_root / "image.bin").write_bytes(b"\x00\xff")
        (head_root / "image.bin").write_bytes(b"\x00\xfe")

        resolver = AsyncMock()
        resolver.resolve.side_effect = [
            RepositorySnapshotRange(
                repository_id=repository_id,
                sync_id=base_sync_id,
                root_path=str(base_root),
            ),
            RepositorySnapshotRange(
                repository_id=repository_id,
                sync_id=head_sync_id,
                root_path=str(head_root),
            ),
        ]

        service = DiffBetweenSyncs(resolver)

        result = await service.execute(repository_id, base_sync_id, head_sync_id)

        assert len(result.file_diffs) == 1
        assert result.file_diffs[0].is_binary is True
        assert result.file_diffs[0].unified_diff == "Binary or non-UTF-8 file changed."
