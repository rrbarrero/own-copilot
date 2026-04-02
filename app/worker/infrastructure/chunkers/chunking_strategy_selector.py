from collections.abc import Callable

from app.worker.domain.chunking_strategy_proto import ChunkingStrategy
from app.worker.domain.document_chunking_context import DocumentChunkingContext
from app.worker.infrastructure.chunkers.generic_recursive_chunking_strategy import (
    GenericRecursiveChunkingStrategy,
)
from app.worker.infrastructure.chunkers.go_chunking_strategy import GoChunkingStrategy
from app.worker.infrastructure.chunkers.markdown_chunking_strategy import (
    MarkdownChunkingStrategy,
)
from app.worker.infrastructure.chunkers.python_chunking_strategy import (
    PythonChunkingStrategy,
)
from app.worker.infrastructure.chunkers.typescript_chunking_strategy import (
    TypeScriptChunkingStrategy,
)


class ChunkingStrategySelector:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self._strategy_factories: dict[str, Callable[[], ChunkingStrategy]] = {
            "md": lambda: MarkdownChunkingStrategy(chunk_size, chunk_overlap),
            "markdown": lambda: MarkdownChunkingStrategy(chunk_size, chunk_overlap),
            "py": lambda: PythonChunkingStrategy(chunk_size, chunk_overlap),
            "python": lambda: PythonChunkingStrategy(chunk_size, chunk_overlap),
            "ts": lambda: TypeScriptChunkingStrategy(chunk_size, chunk_overlap),
            "typescript": lambda: TypeScriptChunkingStrategy(chunk_size, chunk_overlap),
            "go": lambda: GoChunkingStrategy(chunk_size, chunk_overlap),
        }
        self._strategy_cache: dict[str, ChunkingStrategy] = {}
        self._fallback = GenericRecursiveChunkingStrategy(chunk_size, chunk_overlap)

    def select(self, context: DocumentChunkingContext) -> ChunkingStrategy:
        strategy_key = self._resolve_strategy_key(context)
        if strategy_key is None:
            return self._fallback

        if strategy_key in self._strategy_cache:
            return self._strategy_cache[strategy_key]

        factory = self._strategy_factories.get(strategy_key)
        if factory is None:
            return self._fallback

        try:
            strategy = factory()
        except Exception:
            return self._fallback

        self._strategy_cache[strategy_key] = strategy
        return strategy

    def _resolve_strategy_key(self, context: DocumentChunkingContext) -> str | None:
        candidates = (
            self._normalize_extension(context.extension),
            self._normalize_value(context.normalized_format),
            self._normalize_value(context.doc_type),
            self._normalize_value(context.language),
        )

        for candidate in candidates:
            if candidate in self._strategy_factories:
                return candidate

        return None

    @staticmethod
    def _normalize_extension(extension: str | None) -> str | None:
        if not extension:
            return None
        return extension.lower().lstrip(".")

    @staticmethod
    def _normalize_value(value: str | None) -> str | None:
        if not value:
            return None
        return value.strip().lower()
