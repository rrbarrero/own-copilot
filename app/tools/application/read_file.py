import os
from uuid import UUID

from app.tools.domain.errors import (
    RepositoryFileNotFoundError,
    RepositoryFileNotReadableError,
)
from app.tools.domain.path_utils import resolve_safe_path
from app.tools.domain.repository_snapshot_resolver_proto import (
    RepositorySnapshotResolverProto,
)


class ReadFileResult:
    def __init__(
        self,
        repository_id: UUID,
        sync_id: UUID,
        path: str,
        content: str,
        size_bytes: int,
        truncated: bool,
    ):
        self.repository_id = repository_id
        self.sync_id = sync_id
        self.path = path
        self.content = content
        self.size_bytes = size_bytes
        self.truncated = truncated


class ReadFile:
    def __init__(self, resolver: RepositorySnapshotResolverProto):
        self._resolver = resolver

    async def execute(
        self,
        repository_id: UUID,
        path: str,
        max_chars: int = 20000,
        *,
        repository_sync_id: UUID | None = None,
    ) -> ReadFileResult:
        # 1. Resolve snapshot
        snapshot = await self._resolver.resolve(repository_id, repository_sync_id)

        # 2. Resolve safe absolute path within snapshot
        abs_target = resolve_safe_path(snapshot.root_path, path)

        # 3. Check file exists
        if not os.path.isfile(abs_target):
            raise RepositoryFileNotFoundError(path)

        # 4. Read content with size and encoding checks
        size = os.path.getsize(abs_target)

        try:
            with open(abs_target, encoding="utf-8") as f:
                # Read specific amount of chars
                content = f.read(max_chars + 1)
                truncated = len(content) > max_chars
                if truncated:
                    content = content[:max_chars]

                return ReadFileResult(
                    repository_id=repository_id,
                    sync_id=snapshot.sync_id,
                    path=path,
                    content=content,
                    size_bytes=size,
                    truncated=truncated,
                )
        except UnicodeDecodeError:
            raise RepositoryFileNotReadableError(
                path, "Encoding not supported (UTF-8 required)"
            ) from None
        except Exception as e:
            raise RepositoryFileNotReadableError(path, str(e)) from e
