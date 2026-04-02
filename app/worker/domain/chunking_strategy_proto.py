from typing import Protocol


class ChunkingStrategy(Protocol):
    def chunk(self, text: str) -> list[str]: ...
