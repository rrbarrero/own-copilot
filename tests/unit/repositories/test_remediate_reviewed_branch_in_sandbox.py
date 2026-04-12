import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.repositories.application.remediate_reviewed_branch_in_sandbox import (
    RemediateReviewedBranchInSandbox,
)
from app.repositories.domain.remediation import SandboxLogEntry
from app.repositories.domain.repository import Repository
from app.repositories.domain.review import RepositoryBranchReview, ReviewFinding


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


@dataclass
class _FakeRunner:
    workspace: Path
    run_calls: list[tuple[str, list[str], str | None]]
    written_content: str | None = None

    def create_workspace(self, repository_slug: str, branch: str) -> Path:
        del repository_slug, branch
        self.workspace.mkdir(parents=True, exist_ok=True)
        return self.workspace

    def run(
        self,
        *,
        step: str,
        args: list[str],
        cwd: Path | None = None,
        env=None,
        display_args: list[str] | None = None,
    ) -> SandboxLogEntry:
        del env
        self.run_calls.append((step, args, str(cwd) if cwd else None))
        stdout = "ok"
        if step == "git_diff":
            stdout = '-    "seaborn>=0.13.0",'
        if step == "git_status":
            stdout = " M pyproject.toml"
        if step == "git_rev_parse":
            stdout = "abc123"
        return SandboxLogEntry(
            step=step,
            command=" ".join(display_args or args),
            exit_code=0,
            stdout=stdout,
            stderr="",
        )

    def read_text(self, *, step: str, path: Path) -> tuple[str, SandboxLogEntry]:
        return (
            (
                "[project]\n"
                "dependencies = [\n"
                '    "fastapi>=0.1",\n'
                '    "seaborn>=0.13.0",\n'
                "]\n"
            ),
            SandboxLogEntry(
                step=step,
                command=f"read_text {path}",
                exit_code=0,
                stdout=f"Read {path}",
                stderr="",
            ),
        )

    def write_text(self, *, step: str, path: Path, content: str) -> SandboxLogEntry:
        self.written_content = content
        return SandboxLogEntry(
            step=step,
            command=f"write_text {path}",
            exit_code=0,
            stdout=f"Wrote {path}",
            stderr="",
        )


def _build_repository(repository_id):
    return Repository(
        id=repository_id,
        provider="github",
        clone_url="https://github.com/rrbarrero/credit-fraud.git",
        normalized_clone_url="https://github.com/rrbarrero/credit-fraud",
        owner="rrbarrero",
        name="credit-fraud",
        local_path="",
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.mark.asyncio
async def test_execute_remediates_dependency_and_returns_logs(monkeypatch, tmp_path):
    repository_id = uuid4()
    repository_repo = AsyncMock()
    repository_repo.get_by_id.return_value = _build_repository(repository_id)
    review_service = AsyncMock()
    review_service.execute.return_value = RepositoryBranchReview(
        repository_id=repository_id,
        base_branch="main",
        branch="new-feature-branch",
        base_sync_id=uuid4(),
        head_sync_id=uuid4(),
        summary="Unnecessary dependency added.",
        findings=[
            ReviewFinding(
                severity="low",
                path="pyproject.toml",
                title="Unnecessary dependency added",
                rationale="The seaborn package is not used.",
                line_start=14,
                line_end=14,
            )
        ],
    )
    llm = AsyncMock()
    llm.ainvoke.return_value = _FakeResponse(
        json.dumps(
            {
                "path": "pyproject.toml",
                "updated_content": (
                    '[project]\ndependencies = [\n    "fastapi>=0.1",\n]\n'
                ),
                "commit_message": "Remove unused dependency from project config",
                "rationale": (
                    "The unused dependency is removed with no unrelated changes."
                ),
            }
        )
    )
    runner = _FakeRunner(workspace=tmp_path / "sandbox", run_calls=[])

    monkeypatch.setattr(
        "app.repositories.application.remediate_reviewed_branch_in_sandbox.settings.SANDBOX_ALLOWED_REPOSITORY_URL",
        "",
    )
    monkeypatch.setattr(
        "app.repositories.application.remediate_reviewed_branch_in_sandbox.settings.SANDBOX_ALLOWED_BRANCH",
        "",
    )
    monkeypatch.setattr(
        "app.repositories.application.remediate_reviewed_branch_in_sandbox.settings.SANDBOX_GITHUB_TOKEN",
        "secret-token",
    )

    service = RemediateReviewedBranchInSandbox(
        repository_repo=repository_repo,
        review_service=review_service,
        sandbox_runner=runner,
        llm=llm,
    )

    result = await service.execute(
        repository_id=repository_id,
        branch="new-feature-branch",
    )

    assert result.commit_sha == "abc123"
    assert result.changed_files == ["pyproject.toml"]
    assert "seaborn" not in (runner.written_content or "")
    assert runner.written_content == (
        '[project]\ndependencies = [\n    "fastapi>=0.1",\n]\n'
    )
    assert any(log.step == "git_push" for log in result.logs)
    llm.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_rejects_non_allowed_branch_when_guard_is_configured(
    monkeypatch, tmp_path
):
    repository_id = uuid4()
    repository_repo = AsyncMock()
    repository_repo.get_by_id.return_value = _build_repository(repository_id)
    review_service = AsyncMock()
    llm = AsyncMock()
    runner = _FakeRunner(workspace=tmp_path / "sandbox", run_calls=[])

    monkeypatch.setattr(
        "app.repositories.application.remediate_reviewed_branch_in_sandbox.settings.SANDBOX_ALLOWED_BRANCH",
        "new-feature-branch",
    )

    service = RemediateReviewedBranchInSandbox(
        repository_repo=repository_repo,
        review_service=review_service,
        sandbox_runner=runner,
        llm=llm,
    )

    with pytest.raises(ValueError, match="configured branch"):
        await service.execute(repository_id=repository_id, branch="other-branch")
