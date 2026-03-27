from typing import Protocol


class ChunkerProto(Protocol):
    def chunk(self, text: str) -> list[str]: ...
