from uuid import UUID

from pydantic import BaseModel


class DocumentResponseDTO(BaseModel):
    uuid: UUID
    filename: str
    status: str = "uploaded"

    model_config = {
        "json_schema_extra": {
            "example": {
                "uuid": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "guide.md",
                "status": "uploaded",
            }
        }
    }
