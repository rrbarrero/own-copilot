from typing import Protocol

from app.ingestion.domain.document import Document


class DocumentRepoProto(Protocol):
    async def save(self, document: Document) -> None: ...

    async def get_by_uuid(self, uuid: str) -> Document | None: ...
