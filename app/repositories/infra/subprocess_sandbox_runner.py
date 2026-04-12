import subprocess
from pathlib import Path
from typing import Mapping
from uuid import uuid4

from app.repositories.domain.remediation import SandboxLogEntry


class SubprocessSandboxRunner:
    def __init__(self, workspace_root: str):
        self._workspace_root = Path(workspace_root)

    def create_workspace(self, repository_slug: str, branch: str) -> Path:
        workspace = self._workspace_root / repository_slug / self._sanitize(branch) / str(
            uuid4()
        )
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def run(
        self,
        *,
        step: str,
        args: list[str],
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        display_args: list[str] | None = None,
    ) -> SandboxLogEntry:
        proc = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            env=dict(env) if env else None,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return SandboxLogEntry(
            step=step,
            command=" ".join(display_args or args),
            exit_code=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
        )

    def read_text(self, *, step: str, path: Path) -> tuple[str, SandboxLogEntry]:
        content = path.read_text(encoding="utf-8")
        log = SandboxLogEntry(
            step=step,
            command=f"read_text {path}",
            exit_code=0,
            stdout=f"Read {path}",
            stderr="",
        )
        return content, log

    def write_text(self, *, step: str, path: Path, content: str) -> SandboxLogEntry:
        path.write_text(content, encoding="utf-8")
        return SandboxLogEntry(
            step=step,
            command=f"write_text {path}",
            exit_code=0,
            stdout=f"Wrote {path}",
            stderr="",
        )

    def _sanitize(self, value: str) -> str:
        return value.replace("/", "_")
