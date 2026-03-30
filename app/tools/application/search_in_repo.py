import os
from uuid import UUID

from app.tools.domain.models import SearchMatch
from app.tools.domain.path_utils import resolve_safe_path
from app.tools.domain.repository_snapshot_resolver_proto import (
    RepositorySnapshotResolverProto,
)


class SearchInRepo:
    def __init__(self, resolver: RepositorySnapshotResolverProto):
        self._resolver = resolver

    async def execute(
        self,
        repository_id: UUID,
        query: str,
        path_prefix: str | None = None,
        extensions: list[str] | None = None,
        case_sensitive: bool = False,
        limit: int = 50,
    ) -> list[SearchMatch]:
        # 1. Resolve snapshot
        snapshot = await self._resolver.resolve(repository_id)

        # 2. Determine base search path
        base_search_path = (
            resolve_safe_path(snapshot.root_path, path_prefix)
            if path_prefix
            else snapshot.root_path
        )

        matches: list[SearchMatch] = []
        ext_list = [e.lower().lstrip(".") for e in extensions] if extensions else []
        search_q = query if case_sensitive else query.lower()

        # 3. Recursive walk and line-by-line grep
        for root, _, files in os.walk(base_search_path):
            for filename in files:
                if len(matches) >= limit:
                    break

                # Filter by extension
                ext = filename.split(".")[-1].lower() if "." in filename else ""
                if ext_list and ext not in ext_list:
                    continue

                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, snapshot.root_path)

                # 4. Search within file
                try:
                    with open(abs_path, encoding="utf-8") as f:
                        for i, line in enumerate(f, 1):
                            if len(matches) >= limit:
                                break

                            target_line = line if case_sensitive else line.lower()
                            if search_q in target_line:
                                matches.append(
                                    SearchMatch(
                                        path=rel_path,
                                        line_number=i,
                                        line_content=line.strip(),
                                        start_column=target_line.find(search_q) + 1,
                                    )
                                )
                except (UnicodeDecodeError, PermissionError):
                    # Skip unreadable or binary files
                    continue

            if len(matches) >= limit:
                break

        # Sort matches for stability: by path first, then by line number
        matches.sort(key=lambda m: (m.path, m.line_number))

        return matches
