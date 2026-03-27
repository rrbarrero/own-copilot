from app.worker.domain.pipeline_context import PipelineContext
from app.worker.domain.step_proto import StepProto


class Pipeline:
    def __init__(self, steps: list[StepProto]):
        self.steps = steps

    async def run(self, ctx: PipelineContext):
        for step in self.steps:
            await step.run(ctx)
