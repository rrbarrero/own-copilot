from app.ingestion.domain.storage_repo_proto import StorageRepoProto


class InMemoryStorageRepo(StorageRepoProto):
    def __init__(self):
        self._storage: dict[str, str] = {}

    def save(self, path: str, content: str) -> None:
        self._storage[path] = content

    def get(self, path: str) -> str | None:
        return self._storage.get(path)
