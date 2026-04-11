from uuid import UUID

from app.tools.application.find_files import FindFiles
from app.tools.application.read_file import ReadFile, ReadFileResult
from app.tools.application.search_in_repo import SearchInRepo
from app.tools.domain.models import FileMatch, SearchMatch


class RepositoryToolService:
    def __init__(
        self,
        find_files: FindFiles,
        read_file: ReadFile,
        search_in_repo: SearchInRepo,
    ):
        self._find_files = find_files
        self._read_file = read_file
        self._search_in_repo = search_in_repo

    async def find_files(
        self,
        repository_id: UUID,
        path_prefix: str | None = None,
        query: str | None = None,
        extensions: list[str] | None = None,
        limit: int = 50,
        *,
        repository_sync_id: UUID | None = None,
    ) -> list[FileMatch]:
        """
        Finds files in the repository snapshot matching criteria.
        """
        return await self._find_files.execute(
            repository_id=repository_id,
            repository_sync_id=repository_sync_id,
            path_prefix=path_prefix,
            query=query,
            extensions=extensions,
            limit=limit,
        )

    async def read_file(
        self,
        repository_id: UUID,
        path: str,
        max_chars: int = 20000,
        *,
        repository_sync_id: UUID | None = None,
    ) -> ReadFileResult:
        """
        Reads a single file from the repository snapshot.
        """
        return await self._read_file.execute(
            repository_id=repository_id,
            repository_sync_id=repository_sync_id,
            path=path,
            max_chars=max_chars,
        )

    async def search_in_repo(
        self,
        repository_id: UUID,
        query: str,
        path_prefix: str | None = None,
        extensions: list[str] | None = None,
        case_sensitive: bool = False,
        limit: int = 50,
        *,
        repository_sync_id: UUID | None = None,
    ) -> list[SearchMatch]:
        """
        Searches for a literal query across text files in the repository snapshot.
        """
        return await self._search_in_repo.execute(
            repository_id=repository_id,
            repository_sync_id=repository_sync_id,
            query=query,
            path_prefix=path_prefix,
            extensions=extensions,
            case_sensitive=case_sensitive,
            limit=limit,
        )
