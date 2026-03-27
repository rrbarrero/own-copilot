from typing import Protocol

from app.worker.domain.pipeline_context import PipelineContext


class StepProto(Protocol):
    async def run(self, ctx: PipelineContext): ...
