import asyncio
import logging
from time import perf_counter

from app.ingestion.domain.document import SourceType
from app.worker.domain.llm_generator_proto import LLMGeneratorProto
from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.raptor_metadata import (
    ChunkKind,
    RaptorMetadata,
    SummaryLevel,
    SymbolType,
)
from app.worker.domain.step_proto import StepProto
from app.worker.domain.structural_extractor_proto import (
    StructuralExtractorProto,
    StructuralUnit,
)

logger = logging.getLogger(__name__)


class RaptorEnrichmentStep(StepProto):
    """
    Pipeline step that identifies structural units (classes, functions, etc.)
    and generates LLM-powered summaries (RAPTOR nodes).
    """

    def __init__(
        self,
        extractor: StructuralExtractorProto,
        generator: LLMGeneratorProto,
        enabled: bool = True,
        max_units_per_document: int = 8,
        max_unit_chars: int = 6000,
        max_concurrent_llm: int = 2,
    ):
        self.extractor = extractor
        self.generator = generator
        self.enabled = enabled
        self.max_units_per_document = max_units_per_document
        self.max_unit_chars = max_unit_chars
        self._semaphore = asyncio.Semaphore(max_concurrent_llm)

    async def run(self, ctx: PipelineContext):
        started_at = perf_counter()

        if not self.enabled or not ctx.chunks:
            return

        language = self._resolve_language(ctx)
        if language != "python":
            return

        if ctx.source_type != SourceType.REPOSITORY.value:
            return

        # 1. Decode original text again or use normalized
        if ctx.normalized_document:
            text = str(ctx.normalized_document.get("text", ""))
        else:
            if not ctx.original_bytes:
                return
            try:
                text = ctx.original_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return

        # 2. Extract structural units
        units = self.extractor.extract(text, language)
        if not units:
            return

        units = self._select_units(units)
        logger.info(
            "raptor_enrichment.found_units filename=%s units=%d language=%s "
            "selected=%s max_units=%d max_unit_chars=%d",
            ctx.filename,
            len(units),
            language,
            [f"{unit.unit_type}:{unit.name}" for unit in units],
            self.max_units_per_document,
            self.max_unit_chars,
        )

        # 3. Generate summaries in parallel (with semaphore limit)
        current_chunk_idx = len(ctx.chunks)

        async def process_unit(unit: StructuralUnit) -> dict | None:
            unit_started_at = perf_counter()
            unit_text = unit.content[: self.max_unit_chars]
            try:
                async with self._semaphore:
                    llm_started_at = perf_counter()
                    summary = await self.generator.generate_summary(
                        text=unit_text,
                        context=f"File: {ctx.filename}, Language: {language}",
                    )
                    llm_elapsed_ms = (perf_counter() - llm_started_at) * 1000
                if not summary.strip():
                    summary = self._fallback_summary(
                        unit.unit_type,
                        unit.name,
                        unit_text,
                    )
                    used_fallback = True
                else:
                    used_fallback = False

                parent_chunk_indexes = self._resolve_parent_chunk_indexes(ctx, unit)
                metadata = RaptorMetadata(
                    chunk_kind=ChunkKind.SUMMARY,
                    summary_level=self._map_level(unit.unit_type),
                    symbol_type=self._map_type(unit.unit_type),
                    symbol_name=unit.name,
                    parent_path=ctx.source_path,
                    parent_chunk_indexes=parent_chunk_indexes,
                    language=language,
                    source_strategy="raptor",
                ).to_dict()

                logger.info(
                    "raptor_enrichment.summary_generated "
                    "filename=%s unit_type=%s unit_name=%s chars=%d "
                    "llm_elapsed_ms=%.2f total_elapsed_ms=%.2f "
                    "parent_chunks=%d fallback=%s",
                    ctx.filename,
                    unit.unit_type,
                    unit.name,
                    len(unit_text),
                    llm_elapsed_ms,
                    (perf_counter() - unit_started_at) * 1000,
                    len(parent_chunk_indexes),
                    used_fallback,
                )

                return {
                    "content": f"Summary of {unit.unit_type} '{unit.name}': {summary}",
                    "chunk_index": current_chunk_idx,
                    "metadata": metadata,
                }
            except Exception as e:
                llm_elapsed_ms = (perf_counter() - unit_started_at) * 1000
                logger.error(
                    "raptor_enrichment.summary_failed unit_type=%s "
                    "unit_name=%s filename=%s elapsed_ms=%.2f error=%s",
                    unit.unit_type,
                    unit.name,
                    ctx.filename,
                    llm_elapsed_ms,
                    e,
                )
                summary = self._fallback_summary(unit.unit_type, unit.name, unit_text)
                parent_chunk_indexes = self._resolve_parent_chunk_indexes(ctx, unit)
                metadata = RaptorMetadata(
                    chunk_kind=ChunkKind.SUMMARY,
                    summary_level=self._map_level(unit.unit_type),
                    symbol_type=self._map_type(unit.unit_type),
                    symbol_name=unit.name,
                    parent_path=ctx.source_path,
                    parent_chunk_indexes=parent_chunk_indexes,
                    language=language,
                    source_strategy="raptor",
                ).to_dict()
                return {
                    "content": f"Summary of {unit.unit_type} '{unit.name}': {summary}",
                    "chunk_index": current_chunk_idx,
                    "metadata": metadata,
                }

        tasks = [process_unit(unit) for unit in units]
        results = await asyncio.gather(*tasks)

        new_chunks = []
        for i, result in enumerate(results):
            if result:
                result["chunk_index"] = current_chunk_idx + i
                new_chunks.append(result)

        # 4. Append new chunks to context
        ctx.chunks.extend(new_chunks)
        logger.info(
            "raptor_enrichment.completed filename=%s language=%s raw_chunks=%d "
            "summary_chunks=%d total_elapsed_ms=%.2f",
            ctx.filename,
            language,
            current_chunk_idx,
            len(new_chunks),
            (perf_counter() - started_at) * 1000,
        )

    @staticmethod
    def _resolve_language(ctx: PipelineContext) -> str | None:
        if ctx.language:
            return ctx.language

        if not ctx.extension:
            return None

        return {
            "py": "python",
            "ts": "typescript",
            "go": "go",
        }.get(ctx.extension.lower().lstrip("."))

    @staticmethod
    def _resolve_parent_chunk_indexes(
        ctx: PipelineContext,
        unit,  # noqa: ANN001
    ) -> list[int]:
        if unit.unit_type == "module":
            return [
                chunk["chunk_index"]
                for chunk in ctx.chunks
                if chunk.get("metadata", {}).get("chunk_kind") == ChunkKind.RAW
            ]

        parent_indexes: list[int] = []
        unit_content = unit.content.strip()
        if not unit_content:
            return parent_indexes

        for chunk in ctx.chunks:
            metadata = chunk.get("metadata", {})
            if metadata.get("chunk_kind") != ChunkKind.RAW:
                continue

            chunk_content = str(chunk.get("content", "")).strip()
            if not chunk_content:
                continue

            if chunk_content in unit_content or unit_content in chunk_content:
                parent_indexes.append(chunk["chunk_index"])

        return parent_indexes

    def _select_units(self, units: list[StructuralUnit]) -> list[StructuralUnit]:
        if self.max_units_per_document <= 0 or not units:
            return []

        module_units = [unit for unit in units if unit.unit_type == "module"]
        non_module_units = [unit for unit in units if unit.unit_type != "module"]

        selected: list[StructuralUnit] = []
        if module_units:
            selected.append(max(module_units, key=lambda unit: len(unit.content)))

        remaining_slots = self.max_units_per_document - len(selected)
        if remaining_slots <= 0:
            return selected

        ranked_units = sorted(
            non_module_units,
            key=lambda unit: len(unit.content),
            reverse=True,
        )
        selected.extend(ranked_units[:remaining_slots])
        return selected

    def _map_level(self, unit_type: str) -> SummaryLevel:
        if unit_type == "class":
            return SummaryLevel.CLASS
        if unit_type == "module":
            return SummaryLevel.MODULE
        return SummaryLevel.SYMBOL

    def _map_type(self, unit_type: str) -> SymbolType:
        if unit_type == "class":
            return SymbolType.CLASS
        if unit_type == "module":
            return SymbolType.MODULE
        return SymbolType.FUNCTION

    @staticmethod
    def _fallback_summary(unit_type: str, unit_name: str, unit_text: str) -> str:
        normalized_lines = [
            line.strip() for line in unit_text.splitlines() if line.strip()
        ]
        preview = " ".join(normalized_lines[:3])[:240]
        return (
            f"{unit_type.capitalize()} '{unit_name}' extracted from source. "
            f"Preview: {preview}"
        ).strip()
