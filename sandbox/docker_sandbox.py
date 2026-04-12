import subprocess
from pathlib import Path


class DockerSandbox:
    def __init__(self, container_name: str, workspace: str):
        self.container_name = container_name
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

    def write_file(self, path: str, content: str) -> str:
        target = self.workspace / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {path}"

    def read_file(self, path: str) -> str:
        target = self.workspace / path
        if not target.exists():
            raise FileNotFoundError(path)
        return target.read_text(encoding="utf-8")

    def run_command(self, command: str, timeout: int = 30) -> str:
        docker_cmd = [
            "docker", "exec",
            self.container_name,
            "bash", "-lc",
            f"cd /workspace && {command}"
        ]
        proc = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = proc.stdout[-12000:]
        stderr = proc.stderr[-12000:]
        return (
            f"exit_code={proc.returncode}\n"
            f"STDOUT:\n{stdout}\n"
            f"STDERR:\n{stderr}"
        )
