import pytest

from app.worker.domain.document_chunking_context import DocumentChunkingContext
from app.worker.infrastructure.chunkers.chunking_strategy_selector import (
    ChunkingStrategySelector,
)
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


def test_select_markdown_strategy():
    selector = ChunkingStrategySelector()
    ctx = DocumentChunkingContext(extension="md")
    strategy = selector.select(ctx)
    assert isinstance(strategy, MarkdownChunkingStrategy)


def test_select_python_strategy():
    selector = ChunkingStrategySelector()
    ctx = DocumentChunkingContext(extension="py")
    strategy = selector.select(ctx)
    assert isinstance(strategy, PythonChunkingStrategy)


def test_select_go_strategy():
    selector = ChunkingStrategySelector()
    ctx = DocumentChunkingContext(extension="go")
    strategy = selector.select(ctx)
    assert isinstance(strategy, GoChunkingStrategy)


def test_select_typescript_strategy():
    selector = ChunkingStrategySelector()
    ctx = DocumentChunkingContext(extension="ts")
    strategy = selector.select(ctx)
    assert isinstance(strategy, TypeScriptChunkingStrategy)


def test_select_fallback_for_unknown_extension():
    selector = ChunkingStrategySelector()
    ctx = DocumentChunkingContext(extension="txt")
    strategy = selector.select(ctx)
    assert isinstance(strategy, GenericRecursiveChunkingStrategy)


def test_select_fallback_for_no_extension():
    selector = ChunkingStrategySelector()
    ctx = DocumentChunkingContext(extension=None)
    strategy = selector.select(ctx)
    assert isinstance(strategy, GenericRecursiveChunkingStrategy)


def test_select_markdown_strategy_from_doc_type_without_extension():
    selector = ChunkingStrategySelector()
    ctx = DocumentChunkingContext(extension=None, doc_type="markdown")
    strategy = selector.select(ctx)
    assert isinstance(strategy, MarkdownChunkingStrategy)


def test_select_python_strategy_from_language_without_extension():
    selector = ChunkingStrategySelector()
    ctx = DocumentChunkingContext(extension=None, language="python")
    strategy = selector.select(ctx)
    assert isinstance(strategy, PythonChunkingStrategy)


def test_select_normalizes_extension_with_dot_prefix():
    selector = ChunkingStrategySelector()
    ctx = DocumentChunkingContext(extension=".go")
    strategy = selector.select(ctx)
    assert isinstance(strategy, GoChunkingStrategy)


def test_selector_falls_back_if_strategy_init_fails(monkeypatch: pytest.MonkeyPatch):
    selector = ChunkingStrategySelector()

    def broken_factory():
        raise RuntimeError("broken strategy")

    monkeypatch.setitem(selector._strategy_factories, "py", broken_factory)
    ctx = DocumentChunkingContext(extension="py")
    strategy = selector.select(ctx)
    assert isinstance(strategy, GenericRecursiveChunkingStrategy)


def test_markdown_strategy_chunks_correctly():
    strategy = MarkdownChunkingStrategy(chunk_size=100, chunk_overlap=0)
    text = "# Title\n\nThis is a paragraph.\n\n## Subtitle\n\nAnother paragraph."
    chunks = strategy.chunk(text)
    assert len(chunks) > 0
    # Basic check that it doesn't crash and returns some content
    assert any("Title" in c for c in chunks)
