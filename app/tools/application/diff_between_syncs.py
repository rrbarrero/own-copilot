import difflib
import os
from pathlib import Path
from uuid import UUID

from app.tools.domain.models import (
    DiffChangeType,
    RepositoryDiffResult,
    RepositoryFileDiff,
)
from app.tools.domain.repository_snapshot_resolver_proto import (
    RepositorySnapshotResolverProto,
)


class DiffBetweenSyncs:
    def __init__(
        self,
        resolver: RepositorySnapshotResolverProto,
        max_files: int = 50,
        max_diff_lines: int = 200,
    ):
        self._resolver = resolver
        self._max_files = max_files
        self._max_diff_lines = max_diff_lines

    async def execute(
        self,
        repository_id: UUID,
        base_sync_id: UUID,
        head_sync_id: UUID,
    ) -> RepositoryDiffResult:
        base_snapshot = await self._resolver.resolve(repository_id, base_sync_id)
        head_snapshot = await self._resolver.resolve(repository_id, head_sync_id)

        base_files = self._collect_files(base_snapshot.root_path)
        head_files = self._collect_files(head_snapshot.root_path)

        file_diffs: list[RepositoryFileDiff] = []
        for path in sorted(set(base_files) | set(head_files)):
            if len(file_diffs) >= self._max_files:
                break

            base_path = base_files.get(path)
            head_path = head_files.get(path)

            if base_path and head_path:
                if self._same_file(base_path, head_path):
                    continue
                change_type = DiffChangeType.MODIFIED
            elif head_path:
                change_type = DiffChangeType.ADDED
            else:
                change_type = DiffChangeType.DELETED

            file_diffs.append(
                self._build_file_diff(
                    path=path,
                    change_type=change_type,
                    base_path=base_path,
                    head_path=head_path,
                )
            )

        return RepositoryDiffResult(
            repository_id=repository_id,
            base_sync_id=base_snapshot.sync_id,
            head_sync_id=head_snapshot.sync_id,
            file_diffs=file_diffs,
        )

    def _collect_files(self, root_path: str) -> dict[str, str]:
        files: dict[str, str] = {}
        for abs_path in Path(root_path).rglob("*"):
            if abs_path.is_file():
                rel_path = abs_path.relative_to(root_path).as_posix()
                files[rel_path] = str(abs_path)
        return files

    def _same_file(self, base_path: str, head_path: str) -> bool:
        with open(base_path, "rb") as base_file, open(head_path, "rb") as head_file:
            return base_file.read() == head_file.read()

    def _build_file_diff(
        self,
        path: str,
        change_type: DiffChangeType,
        base_path: str | None,
        head_path: str | None,
    ) -> RepositoryFileDiff:
        base_text = self._read_text(base_path)
        head_text = self._read_text(head_path)
        is_binary = base_text is None or head_text is None

        if is_binary:
            return RepositoryFileDiff(
                path=path,
                change_type=change_type,
                unified_diff="Binary or non-UTF-8 file changed.",
                additions=0,
                deletions=0,
                is_binary=True,
            )

        diff_lines = list(
            difflib.unified_diff(
                [] if base_text is None else base_text.splitlines(),
                [] if head_text is None else head_text.splitlines(),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
                n=3,
            )
        )

        additions = sum(
            1
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        deletions = sum(
            1
            for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )

        if len(diff_lines) > self._max_diff_lines:
            diff_lines = diff_lines[: self._max_diff_lines]
            diff_lines.append("@@ diff truncated @@")

        return RepositoryFileDiff(
            path=path,
            change_type=change_type,
            unified_diff="\n".join(diff_lines),
            additions=additions,
            deletions=deletions,
            is_binary=False,
        )

    def _read_text(self, path: str | None) -> str | None:
        if path is None:
            return ""

        if not os.path.isfile(path):
            return None

        try:
            with open(path, encoding="utf-8") as file:
                return file.read()
        except UnicodeDecodeError:
            return None
