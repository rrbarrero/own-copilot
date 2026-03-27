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
