from pathlib import Path

from app.ingestion.domain.storage_repo_proto import StorageRepoProto


class InFilesystemStorageRepo(StorageRepoProto):
    def __init__(self, base_path: str):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def save(self, path: str, content: bytes) -> None:
        file_path = self._base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

    def get(self, path: str) -> bytes | None:
        file_path = self._base_path / path
        if not file_path.exists() or not file_path.is_file():
            return None
        return file_path.read_bytes()
