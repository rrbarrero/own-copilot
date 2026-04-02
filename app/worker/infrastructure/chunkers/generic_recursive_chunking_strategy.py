from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.worker.domain.chunking_strategy_proto import ChunkingStrategy


class GenericRecursiveChunkingStrategy(ChunkingStrategy):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk(self, text: str) -> list[str]:
        return self._splitter.split_text(text)
