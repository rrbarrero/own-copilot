import pytest

from app.ingestion.domain.document import SourceType
from app.worker.application.steps.raptor_enrichment_step import RaptorEnrichmentStep
from app.worker.domain.llm_generator_proto import LLMGeneratorProto
from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.raptor_metadata import ChunkKind, RaptorMetadata, SummaryLevel
from app.worker.domain.structural_extractor_proto import StructuralUnit
from app.worker.infrastructure.extractors.python_structural_extractor import (
    PythonStructuralExtractor,
)


def test_raptor_metadata_serialization():
    meta = RaptorMetadata(
        chunk_kind=ChunkKind.SUMMARY,
        summary_level=SummaryLevel.CLASS,
        symbol_name="MyClass",
        parent_path="app/main.py",
        language="python",
        source_strategy="raptor",
    )
    d = meta.to_dict()
    assert d["chunk_kind"] == "summary"
    assert d["summary_level"] == "class"
    assert d["symbol_name"] == "MyClass"
    assert d["parent_path"] == "app/main.py"
    assert d["language"] == "python"
    assert d["source_strategy"] == "raptor"


def test_raptor_raw_metadata_does_not_tag_source_strategy():
    meta = RaptorMetadata(
        chunk_kind=ChunkKind.RAW,
        language="python",
    )

    assert "source_strategy" not in meta.to_dict()


def test_raptor_select_units_keeps_module_and_largest_non_module_units():
    step = RaptorEnrichmentStep(
        extractor=PythonStructuralExtractor(),
        generator=StubGenerator(),
        max_units_per_document=2,
    )

    units = [
        StructuralUnit(name="small_fn", unit_type="function", content="x" * 100),
        StructuralUnit(name="big_fn", unit_type="function", content="x" * 400),
        StructuralUnit(name="module", unit_type="module", content="x" * 250),
        StructuralUnit(name="mid_fn", unit_type="function", content="x" * 200),
    ]

    selected = step._select_units(units)

    assert [(unit.unit_type, unit.name) for unit in selected] == [
        ("module", "module"),
        ("function", "big_fn"),
    ]


def test_python_structural_extractor_basic():
    extractor = PythonStructuralExtractor()
    code = """
class MyClass:
    def method(self):
        pass

def top_level_func():
    return 42
"""
    units = extractor.extract(code, "python")

    # Should find 1 class, 1 function, and 1 module
    # Note: currently our basic ast extractor identifies ClassDef and
    # FunctionDef at top level
    class_units = [u for u in units if u.unit_type == "class"]
    func_units = [u for u in units if u.unit_type == "function"]
    module_units = [u for u in units if u.unit_type == "module"]

    assert len(class_units) == 1
    assert class_units[0].name == "MyClass"
    assert "class MyClass" in class_units[0].content

    assert len(func_units) == 1
    assert func_units[0].name == "top_level_func"
    assert "def top_level_func" in func_units[0].content

    assert len(module_units) == 1
    assert module_units[0].name == "module"


class StubGenerator(LLMGeneratorProto):
    async def generate_summary(self, text: str, context: str = "") -> str:
        return f"summary::{context}::{text[:20]}"


@pytest.mark.asyncio
async def test_raptor_enrichment_infers_language_and_keeps_parent_chunk_indexes():
    step = RaptorEnrichmentStep(
        extractor=PythonStructuralExtractor(),
        generator=StubGenerator(),
        max_units_per_document=10,
        max_unit_chars=2000,
    )
    ctx = PipelineContext(
        job_id="job-1",
        job_type="process_document",
        payload={},
        filename="sample.py",
        extension="py",
        source_path="pkg/sample.py",
        source_type=SourceType.REPOSITORY.value,
        original_bytes=(
            b"class MyClass:\n"
            b"    def run(self):\n"
            b"        return 1\n\n"
            b"def top_level_func():\n"
            b"    return 42\n"
        ),
        chunks=[
            {
                "content": "class MyClass:\n    def run(self):\n        return 1",
                "chunk_index": 0,
                "metadata": {"chunk_kind": "raw"},
            },
            {
                "content": "def top_level_func():\n    return 42",
                "chunk_index": 1,
                "metadata": {"chunk_kind": "raw"},
            },
        ],
    )

    await step.run(ctx)

    summary_chunks = [
        chunk
        for chunk in ctx.chunks
        if chunk["metadata"].get("chunk_kind") == "summary"
    ]
    assert len(summary_chunks) == 3

    class_summary = next(
        chunk
        for chunk in summary_chunks
        if chunk["metadata"].get("symbol_name") == "MyClass"
    )
    assert class_summary["metadata"]["language"] == "python"
    assert class_summary["metadata"]["parent_chunk_indexes"] == [0]

    module_summary = next(
        chunk
        for chunk in summary_chunks
        if chunk["metadata"].get("summary_level") == "module"
    )
    assert module_summary["metadata"]["parent_chunk_indexes"] == [0, 1]
