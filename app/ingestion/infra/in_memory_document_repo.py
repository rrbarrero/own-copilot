from uuid import UUID

from app.ingestion.domain.document import Document
from app.ingestion.domain.document_repo_proto import DocumentRepoProto


class InMemoryDocumentRepo(DocumentRepoProto):
    def __init__(self):
        self._documents: dict[UUID, Document] = {}

    async def save(self, document: Document) -> None:
        self._documents[document.uuid] = document

    async def get_by_uuid(self, uuid: str) -> Document | None:
        try:
            doc_uuid = UUID(uuid)
            return self._documents.get(doc_uuid)
        except ValueError:
            return None

    async def get_by_hash(self, content_hash: str) -> Document | None:
        for doc in self._documents.values():
            if doc.content_hash == content_hash:
                return doc
        return None

    async def get_by_batch_id(self, batch_id: UUID) -> list[Document]:
        return [
            doc for doc in self._documents.values() if doc.upload_batch_id == batch_id
        ]

    async def list_by_repository_sync_id(self, sync_id: UUID) -> list[Document]:
        return [
            doc for doc in self._documents.values() if doc.repository_sync_id == sync_id
        ]

    async def get_by_repository_and_source_id(
        self, repository_id: UUID, source_id: str
    ) -> Document | None:
        for doc in self._documents.values():
            if doc.repository_id == repository_id and doc.source_id == source_id:
                return doc
        return None

    async def list_by_repository_id(self, repository_id: UUID) -> list[Document]:
        return [
            doc
            for doc in self._documents.values()
            if doc.repository_id == repository_id
        ]

    async def delete_by_uuids(self, uuids: list[UUID]) -> None:
        for uid in uuids:
            if uid in self._documents:
                del self._documents[uid]
