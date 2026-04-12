import json
from pathlib import Path
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.repositories.application.review_repository_branch_against_main import (
    ReviewRepositoryBranchAgainstMain,
)
from app.repositories.domain.remediation import (
    RepositoryBranchRemediation,
    SandboxLogEntry,
)
from app.repositories.domain.repository_repo_proto import RepositoryRepoProto
from app.repositories.domain.sandbox_runner_proto import SandboxRunnerProto


class RemediateReviewedBranchInSandbox:
    _SYSTEM_PROMPT = (
        "You are a senior software engineer applying a minimal safe fix for a single "
        "review finding.\n"
        "You will receive one finding and the full current content of the target "
        "file.\n"
        "Return ONLY a JSON object with keys: path, updated_content, commit_message, "
        "rationale.\n"
        "Rules:\n"
        "- Edit only the target file from the finding.\n"
        "- Keep the change minimal and directly related to the finding.\n"
        "- Do not add unrelated refactors.\n"
        "- updated_content must contain the full file after the fix.\n"
        "- commit_message must be concise and imperative.\n"
    )

    def __init__(
        self,
        repository_repo: RepositoryRepoProto,
        review_service: ReviewRepositoryBranchAgainstMain,
        sandbox_runner: SandboxRunnerProto,
        llm: BaseChatModel,
    ):
        self._repository_repo = repository_repo
        self._review_service = review_service
        self._sandbox_runner = sandbox_runner
        self._llm = llm

    async def execute(
        self,
        repository_id: UUID,
        branch: str,
    ) -> RepositoryBranchRemediation:
        normalized_branch = branch.strip()
        if not normalized_branch:
            raise ValueError("Branch is required.")

        repository = await self._repository_repo.get_by_id(repository_id)
        if repository is None:
            raise LookupError(f"Repository {repository_id} was not found.")

        self._ensure_scope_guard(repository.clone_url, normalized_branch)

        review = await self._review_service.execute(repository_id, normalized_branch)
        finding = self._select_finding(review.findings)
        if finding is None:
            raise ValueError("The review did not produce any finding to remediate.")

        workspace = self._sandbox_runner.create_workspace(
            repository.name,
            normalized_branch,
        )
        repo_dir = workspace / "repo"
        logs: list[SandboxLogEntry] = []

        logs.append(
            self._run_or_raise(
                step="git_clone",
                args=[
                    "git",
                    "clone",
                    "--branch",
                    normalized_branch,
                    "--single-branch",
                    repository.clone_url,
                    str(repo_dir),
                ],
            )
        )
        logs.append(
            self._run_or_raise(
                step="git_config_user_name",
                args=["git", "config", "user.name", settings.SANDBOX_GIT_USER_NAME],
                cwd=repo_dir,
            )
        )
        logs.append(
            self._run_or_raise(
                step="git_config_user_email",
                args=["git", "config", "user.email", settings.SANDBOX_GIT_USER_EMAIL],
                cwd=repo_dir,
            )
        )

        target_path = repo_dir / finding.path
        original_content, read_log = self._sandbox_runner.read_text(
            step="read_target_file",
            path=target_path,
        )
        logs.append(read_log)

        remediation_plan = await self._build_remediation_plan(
            review_summary=review.summary,
            repository_name=repository.name,
            branch=normalized_branch,
            finding=finding,
            file_content=original_content,
        )
        planned_path = str(remediation_plan.get("path", "")).strip()
        if planned_path != finding.path:
            raise ValueError(
                "The remediation plan targeted a different file than the finding."
            )

        updated_content = str(remediation_plan.get("updated_content", ""))
        if updated_content == original_content:
            raise ValueError("The remediation plan did not modify the target file.")
        if not updated_content.strip():
            raise ValueError("The remediation plan returned empty file content.")

        logs.append(
            self._sandbox_runner.write_text(
                step="write_target_file",
                path=target_path,
                content=updated_content,
            )
        )
        logs.append(
            self._run_or_raise(
                step="git_diff",
                args=["git", "diff", "--", finding.path],
                cwd=repo_dir,
            )
        )
        logs.append(
            self._run_or_raise(
                step="git_status",
                args=["git", "status", "--short"],
                cwd=repo_dir,
            )
        )
        logs.append(
            self._run_or_raise(
                step="git_add",
                args=["git", "add", finding.path],
                cwd=repo_dir,
            )
        )
        commit_message = str(remediation_plan.get("commit_message", "")).strip()
        if not commit_message:
            raise ValueError("The remediation plan did not provide a commit message.")
        logs.append(
            self._run_or_raise(
                step="git_commit",
                args=["git", "commit", "-m", commit_message],
                cwd=repo_dir,
            )
        )

        authenticated_url = self._build_authenticated_url(repository.clone_url)
        logs.append(
            self._run_or_raise(
                step="git_remote_set_url",
                args=["git", "remote", "set-url", "origin", authenticated_url],
                cwd=repo_dir,
                display_args=[
                    "git",
                    "remote",
                    "set-url",
                    "origin",
                    self._redact_authenticated_url(authenticated_url),
                ],
            )
        )
        logs.append(
            self._run_or_raise(
                step="git_push",
                args=["git", "push", "origin", normalized_branch],
                cwd=repo_dir,
            )
        )
        commit_log = self._run_or_raise(
            step="git_rev_parse",
            args=["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
        )
        logs.append(commit_log)

        return RepositoryBranchRemediation(
            repository_id=repository_id,
            branch=normalized_branch,
            review_summary=review.summary,
            remediated_finding_title=finding.title,
            commit_sha=commit_log.stdout.strip(),
            changed_files=[finding.path],
            logs=logs,
        )

    def _ensure_scope_guard(self, clone_url: str, branch: str) -> None:
        allowed_repo = settings.SANDBOX_ALLOWED_REPOSITORY_URL.strip()
        allowed_branch = settings.SANDBOX_ALLOWED_BRANCH.strip()
        if allowed_repo and clone_url != allowed_repo:
            raise ValueError(
                "Sandbox remediation is restricted to the configured repository."
            )
        if allowed_branch and branch != allowed_branch:
            raise ValueError(
                "Sandbox remediation is restricted to the configured branch."
            )

    def _select_finding(self, findings):
        if not findings:
            return None
        severity_rank = {"high": 0, "medium": 1, "low": 2}
        return sorted(
            findings,
            key=lambda finding: severity_rank.get(str(finding.severity), 99),
        )[0]

    def _run_or_raise(
        self,
        *,
        step: str,
        args: list[str],
        cwd: Path | None = None,
        display_args: list[str] | None = None,
    ) -> SandboxLogEntry:
        log = self._sandbox_runner.run(
            step=step,
            args=args,
            cwd=cwd,
            display_args=display_args,
        )
        if log.exit_code != 0:
            raise RuntimeError(
                f"Sandbox step {step} failed with exit code "
                f"{log.exit_code}: {log.stderr}"
            )
        return log

    async def _build_remediation_plan(
        self,
        *,
        review_summary: str,
        repository_name: str,
        branch: str,
        finding,
        file_content: str,
    ) -> dict:
        prompt = "\n".join(
            [
                f"Repository: {repository_name}",
                f"Branch: {branch}",
                f"Review summary: {review_summary}",
                f"Finding path: {finding.path}",
                f"Finding title: {finding.title}",
                f"Finding severity: {finding.severity}",
                f"Finding rationale: {finding.rationale}",
                "Current file content:",
                file_content,
            ]
        )
        response = await self._llm.ainvoke(
            [
                SystemMessage(content=self._SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        return self._parse_remediation_plan(str(response.content))

    def _parse_remediation_plan(self, content: str) -> dict:
        normalized = content.strip()
        if "```json" in normalized:
            normalized = normalized.split("```json", 1)[1].split("```", 1)[0].strip()
        elif normalized.startswith("```"):
            normalized = normalized.split("```", 1)[1].rsplit("```", 1)[0].strip()

        try:
            data = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "The remediation model did not return valid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError("The remediation model did not return an object.")
        return data

    def _build_authenticated_url(self, clone_url: str) -> str:
        token = settings.SANDBOX_GITHUB_TOKEN.strip()
        if not token:
            raise ValueError(
                "SANDBOX_GITHUB_TOKEN is required to push remediation commits."
            )
        if not clone_url.startswith("https://"):
            raise ValueError("Sandbox remediation only supports HTTPS clone URLs.")
        return clone_url.replace("https://", f"https://x-access-token:{token}@", 1)

    def _redact_authenticated_url(self, authenticated_url: str) -> str:
        token = settings.SANDBOX_GITHUB_TOKEN.strip()
        return authenticated_url.replace(token, "***")
