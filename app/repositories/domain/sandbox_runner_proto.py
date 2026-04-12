from pathlib import Path
from typing import Mapping, Protocol

from app.repositories.domain.remediation import SandboxLogEntry


class SandboxRunnerProto(Protocol):
    def create_workspace(self, repository_slug: str, branch: str) -> Path: ...

    def run(
        self,
        *,
        step: str,
        args: list[str],
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        display_args: list[str] | None = None,
    ) -> SandboxLogEntry: ...

    def read_text(self, *, step: str, path: Path) -> tuple[str, SandboxLogEntry]: ...

    def write_text(self, *, step: str, path: Path, content: str) -> SandboxLogEntry: ...
