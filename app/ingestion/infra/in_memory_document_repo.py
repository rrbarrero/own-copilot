from uuid import UUID

from app.ingestion.domain.chunk_repo_proto import ChunkRepoProto
from app.ingestion.domain.document import Document
from app.ingestion.domain.document_repo_proto import DocumentRepoProto


class InMemoryDocumentRepo(DocumentRepoProto, ChunkRepoProto):
    def __init__(self):
        self._documents: dict[UUID, Document] = {}
        # document_uuid -> list[dict]
        self._chunks: dict[str, list[dict]] = {}

    async def save(self, document: Document) -> None:
        self._documents[document.uuid] = document

    async def get_by_uuid(self, uuid: str) -> Document | None:
        try:
            doc_uuid = UUID(uuid)
            return self._documents.get(doc_uuid)
        except ValueError:
            return None

    async def get_by_batch_id(self, batch_id: UUID) -> list[Document]:
        return [
            doc for doc in self._documents.values() if doc.upload_batch_id == batch_id
        ]

    async def save_chunks(self, document_uuid: str, chunks: list[dict]) -> None:
        self._chunks[str(document_uuid)] = chunks

    def get_chunks(self, document_uuid: str) -> list[dict]:
        return self._chunks.get(str(document_uuid), [])
