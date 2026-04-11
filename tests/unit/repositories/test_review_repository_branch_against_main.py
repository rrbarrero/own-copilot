from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.repositories.application.review_repository_branch_against_main import (
    ReviewRepositoryBranchAgainstMain,
)
from app.tools.domain.models import (
    DiffChangeType,
    RepositoryDiffResult,
    RepositoryFileDiff,
)


class _FakeResponse:
    def __init__(self, content: str):
        self.content = content


class TestReviewRepositoryBranchAgainstMain:
    @pytest.mark.asyncio
    async def test_execute_returns_llm_findings(self):
        repository_id = uuid4()
        main_sync_id = uuid4()
        feature_sync_id = uuid4()

        sync_repo = AsyncMock()
        sync_repo.get_latest_completed_by_repository_and_branch.side_effect = [
            SimpleNamespace(id=main_sync_id),
            SimpleNamespace(id=feature_sync_id),
        ]

        diff_service = AsyncMock()
        diff_service.execute.return_value = RepositoryDiffResult(
            repository_id=repository_id,
            base_sync_id=main_sync_id,
            head_sync_id=feature_sync_id,
            file_diffs=[
                RepositoryFileDiff(
                    path="app/service.py",
                    change_type=DiffChangeType.MODIFIED,
                    unified_diff="@@ -1 +1 @@\n-value = 1\n+value = 2",
                    additions=1,
                    deletions=1,
                )
            ],
        )

        llm = AsyncMock()
        llm.ainvoke.return_value = _FakeResponse(
            """
            {
              "summary": "One regression risk found.",
              "findings": [
                {
                  "severity": "high",
                  "path": "app/service.py",
                  "title": "Changed default value",
                  "rationale": "This alters behavior for existing callers.",
                  "line_start": 1,
                  "line_end": 1
                }
              ]
            }
            """
        )

        service = ReviewRepositoryBranchAgainstMain(sync_repo, diff_service, llm)

        result = await service.execute(repository_id=repository_id, branch="feature/x")

        assert result.base_branch == "main"
        assert result.branch == "feature/x"
        assert result.base_sync_id == main_sync_id
        assert result.head_sync_id == feature_sync_id
        assert result.summary == "One regression risk found."
        assert len(result.findings) == 1
        assert result.findings[0].severity == "high"
        assert result.findings[0].path == "app/service.py"

    @pytest.mark.asyncio
    async def test_execute_returns_empty_findings_when_no_diff(self):
        repository_id = uuid4()
        main_sync_id = uuid4()
        feature_sync_id = uuid4()

        sync_repo = AsyncMock()
        sync_repo.get_latest_completed_by_repository_and_branch.side_effect = [
            SimpleNamespace(id=main_sync_id),
            SimpleNamespace(id=feature_sync_id),
        ]

        diff_service = AsyncMock()
        diff_service.execute.return_value = RepositoryDiffResult(
            repository_id=repository_id,
            base_sync_id=main_sync_id,
            head_sync_id=feature_sync_id,
            file_diffs=[],
        )

        llm = AsyncMock()

        service = ReviewRepositoryBranchAgainstMain(sync_repo, diff_service, llm)

        result = await service.execute(repository_id=repository_id, branch="feature/x")

        assert result.findings == []
        assert "No changes detected" in result.summary
        llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_rejects_main_branch(self):
        service = ReviewRepositoryBranchAgainstMain(
            sync_repo=AsyncMock(),
            diff_service=AsyncMock(),
            llm=AsyncMock(),
        )

        with pytest.raises(ValueError, match="non-main branch"):
            await service.execute(repository_id=uuid4(), branch="main")
