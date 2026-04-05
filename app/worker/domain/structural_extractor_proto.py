from abc import ABC, abstractmethod

from pydantic import BaseModel


class StructuralUnit(BaseModel):
    name: str
    unit_type: str
    content: str
    start_chunk_idx: int = 0
    end_chunk_idx: int = 0


class StructuralExtractorProto(ABC):
    @abstractmethod
    def extract(self, text: str, language: str) -> list[StructuralUnit]:
        pass
