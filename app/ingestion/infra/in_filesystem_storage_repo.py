from anyio import Path

from app.ingestion.domain.storage_repo_proto import StorageRepoProto


class InFilesystemStorageRepo(StorageRepoProto):
    def __init__(self, base_path: str):
        self._base_path = Path(base_path)

    async def _ensure_base_dir(self):
        if not await self._base_path.exists():
            await self._base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, path: str, content: bytes) -> None:
        await self._ensure_base_dir()
        file_path = self._base_path / path
        await file_path.parent.mkdir(parents=True, exist_ok=True)
        await file_path.write_bytes(content)

    async def get(self, path: str) -> bytes | None:
        file_path = self._base_path / path
        if not await file_path.exists() or not await file_path.is_file():
            return None
        return await file_path.read_bytes()
