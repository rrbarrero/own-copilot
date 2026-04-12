from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SandboxLogEntry:
    step: str
    command: str
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RepositoryBranchRemediation:
    repository_id: UUID
    branch: str
    review_summary: str
    remediated_finding_title: str
    commit_sha: str
    changed_files: list[str]
    logs: list[SandboxLogEntry]
