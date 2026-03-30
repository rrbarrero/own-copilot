import os
from uuid import UUID

from app.tools.domain.models import FileMatch
from app.tools.domain.path_utils import resolve_safe_path
from app.tools.domain.repository_snapshot_resolver_proto import (
    RepositorySnapshotResolverProto,
)


class FindFiles:
    def __init__(self, resolver: RepositorySnapshotResolverProto):
        self._resolver = resolver

    async def execute(
        self,
        repository_id: UUID,
        path_prefix: str | None = None,
        query: str | None = None,
        extensions: list[str] | None = None,
        limit: int = 50,
    ) -> list[FileMatch]:
        # 1. Resolve snapshot
        snapshot = await self._resolver.resolve(repository_id)

        # 2. Determine base search path
        base_search_path = (
            resolve_safe_path(snapshot.root_path, path_prefix)
            if path_prefix
            else snapshot.root_path
        )

        matches: list[FileMatch] = []
        ext_list = [e.lower().lstrip(".") for e in extensions] if extensions else []

        # 3. Recursive walk
        for root, _, files in os.walk(base_search_path):
            for filename in files:
                if len(matches) >= limit:
                    break

                # Filter by extension
                ext = filename.split(".")[-1].lower() if "." in filename else ""
                if ext_list and ext not in ext_list:
                    continue

                # Filter by query
                if query and query.lower() not in filename.lower():
                    continue

                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, snapshot.root_path)

                matches.append(
                    FileMatch(
                        path=rel_path,
                        filename=filename,
                        extension=ext,
                        size_bytes=os.path.getsize(abs_path),
                    )
                )

            if len(matches) >= limit:
                break

        # 4. Sort results for stability
        matches.sort(key=lambda m: m.path)

        return matches
