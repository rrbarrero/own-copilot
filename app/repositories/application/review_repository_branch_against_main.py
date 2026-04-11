import json
from uuid import UUID

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.repositories.domain.repository_sync_repo_proto import RepositorySyncRepoProto
from app.repositories.domain.review import RepositoryBranchReview, ReviewFinding
from app.tools.application.diff_between_syncs import DiffBetweenSyncs


class ReviewRepositoryBranchAgainstMain:
    _BASE_BRANCH = "main"
    _SYSTEM_PROMPT = (
        "You are a senior code reviewer. Review only the provided diff. "
        "Return ONLY a JSON object with keys: summary and findings. "
        "findings must be an array of objects with keys: severity, path, "
        "title, rationale, line_start, line_end. "
        "Severity must be one of: low, medium, high. "
        "If there are no problems, return an empty findings array."
    )

    def __init__(
        self,
        sync_repo: RepositorySyncRepoProto,
        diff_service: DiffBetweenSyncs,
        llm: BaseChatModel,
    ):
        self._sync_repo = sync_repo
        self._diff_service = diff_service
        self._llm = llm

    async def execute(
        self,
        repository_id: UUID,
        branch: str,
    ) -> RepositoryBranchReview:
        normalized_branch = branch.strip()
        if not normalized_branch:
            raise ValueError("Branch is required.")
        if normalized_branch == self._BASE_BRANCH:
            raise ValueError("Branch review against main requires a non-main branch.")

        base_sync = await self._sync_repo.get_latest_completed_by_repository_and_branch(
            repository_id, self._BASE_BRANCH
        )
        if base_sync is None:
            raise LookupError(
                f"No completed sync found for repository {repository_id} on main."
            )

        head_sync = await self._sync_repo.get_latest_completed_by_repository_and_branch(
            repository_id, normalized_branch
        )
        if head_sync is None:
            raise LookupError(
                "No completed sync found for repository "
                f"{repository_id} on branch {normalized_branch}."
            )

        diff_result = await self._diff_service.execute(
            repository_id=repository_id,
            base_sync_id=base_sync.id,
            head_sync_id=head_sync.id,
        )

        if not diff_result.file_diffs:
            return RepositoryBranchReview(
                repository_id=repository_id,
                base_branch=self._BASE_BRANCH,
                branch=normalized_branch,
                base_sync_id=base_sync.id,
                head_sync_id=head_sync.id,
                summary=(
                    "No changes detected between main and the requested branch."
                ),
                findings=[],
            )

        prompt = self._build_prompt(branch=normalized_branch, diff_result=diff_result)
        response = await self._llm.ainvoke(
            [
                SystemMessage(content=self._SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        parsed = self._parse_response(str(response.content))

        return RepositoryBranchReview(
            repository_id=repository_id,
            base_branch=self._BASE_BRANCH,
            branch=normalized_branch,
            base_sync_id=base_sync.id,
            head_sync_id=head_sync.id,
            summary=str(parsed.get("summary", "")).strip()
            or "Review completed without a summary.",
            findings=[
                ReviewFinding(
                    severity=str(item.get("severity", "medium")),  # type: ignore[arg-type]
                    path=str(item.get("path", "")),
                    title=str(item.get("title", "")).strip() or "Review finding",
                    rationale=str(item.get("rationale", "")).strip()
                    or "No rationale provided.",
                    line_start=self._to_optional_int(item.get("line_start")),
                    line_end=self._to_optional_int(item.get("line_end")),
                )
                for item in parsed.get("findings", [])
                if str(item.get("path", "")).strip()
            ],
        )

    def _build_prompt(self, branch: str, diff_result) -> str:
        sections = [
            f"Review branch: {branch}",
            f"Base branch: {self._BASE_BRANCH}",
            "Changed files:",
        ]
        for file_diff in diff_result.file_diffs:
            sections.append(
                f"- {file_diff.path} [{file_diff.change_type}] "
                f"+{file_diff.additions} -{file_diff.deletions}"
            )
            sections.append(file_diff.unified_diff)

        return "\n".join(sections)

    def _parse_response(self, content: str) -> dict:
        normalized = content.strip()
        if "```json" in normalized:
            normalized = normalized.split("```json", 1)[1].split("```", 1)[0].strip()
        elif normalized.startswith("```"):
            normalized = normalized.split("```", 1)[1].rsplit("```", 1)[0].strip()

        try:
            data = json.loads(normalized)
        except json.JSONDecodeError:
            return {
                "summary": "Review completed but the model did not return JSON.",
                "findings": [],
            }

        findings = data.get("findings", [])
        if not isinstance(findings, list):
            findings = []
        return {
            "summary": data.get("summary", ""),
            "findings": findings,
        }

    def _to_optional_int(self, value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
