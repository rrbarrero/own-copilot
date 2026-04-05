from enum import StrEnum

from pydantic import BaseModel, Field


class ChunkKind(StrEnum):
    RAW = "raw"
    SUMMARY = "summary"


class SummaryLevel(StrEnum):
    SYMBOL = "symbol"
    CLASS = "class"
    MODULE = "module"


class SymbolType(StrEnum):
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    MODULE = "module"


class RaptorMetadata(BaseModel):
    chunk_kind: ChunkKind = Field(default=ChunkKind.RAW)
    summary_level: SummaryLevel | None = None
    symbol_type: SymbolType | None = None
    symbol_name: str | None = None
    parent_path: str | None = None
    parent_chunk_indexes: list[int] = Field(default_factory=list)
    language: str | None = None
    source_strategy: str | None = None

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)
