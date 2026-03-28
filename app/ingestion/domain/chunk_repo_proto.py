from typing import Protocol


class ChunkRepoProto(Protocol):
    async def save_chunks(self, document_uuid: str, chunks: list[dict]) -> None: ...
