# app/worker/infrastructure/chunkers/recursive_character_chunker.py
# (Using LangChain splitters which are already standard for RAG projects)
from langchain_text_splitters import RecursiveCharacterTextSplitter


class RecursiveCharacterChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def chunk(self, text: str) -> list[str]:
        return self._splitter.split_text(text)
