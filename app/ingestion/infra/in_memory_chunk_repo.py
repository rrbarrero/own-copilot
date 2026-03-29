from app.ingestion.domain.chunk_repo_proto import ChunkRepoProto


class InMemoryChunkRepo(ChunkRepoProto):
    def __init__(self):
        # document_uuid -> list[dict]
        self._chunks: dict[str, list[dict]] = {}

    async def save_chunks(self, document_uuid: str, chunks: list[dict]) -> None:
        self._chunks[str(document_uuid)] = chunks

    def get_chunks(self, document_uuid: str) -> list[dict]:
        return self._chunks.get(str(document_uuid), [])
