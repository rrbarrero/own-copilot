import logging

from app.agentic.domain.graph_state import AgentGraphState
from app.repositories.application.review_repository_branch_against_main import (
    ReviewRepositoryBranchAgainstMain,
)

logger = logging.getLogger(__name__)


class RunReviewBranchNode:
    """
    Executes a repository branch review against main and prepares
    a final answer directly from the review result.
    """

    def __init__(self, review_service: ReviewRepositoryBranchAgainstMain):
        self._review_service = review_service

    async def __call__(self, state: AgentGraphState) -> dict:
        last_tc = state["tool_calls"][-1]
        params = last_tc.get("parameters", {})
        branch = str(params.get("branch", "")).strip()
        repo_id = state["scope"].repository_id

        logger.info(
            "graph_node.review_branch conversation_id=%s repository_id=%s branch=%r",
            state["conversation_id"],
            repo_id,
            branch,
        )

        if not repo_id:
            answer = "I can't review a branch without a repository scope."
            return {
                "answer": answer,
                "tool_context": answer,
                "reasoning_trace": state["reasoning_trace"]
                + ["Failed to run review_branch: Missing repo ID."],
            }

        if not branch:
            answer = (
                "I couldn't identify which branch to review. "
                "Please specify the branch explicitly."
            )
            return {
                "answer": answer,
                "tool_context": answer,
                "reasoning_trace": state["reasoning_trace"]
                + ["Failed to run review_branch: Missing branch parameter."],
            }

        try:
            review = await self._review_service.execute(
                repository_id=repo_id,
                branch=branch,
            )
        except Exception as exc:
            answer = f"Failed to review branch {branch}: {exc}"
            logger.warning(
                "graph_node.review_branch.error conversation_id=%s branch=%r error=%r",
                state["conversation_id"],
                branch,
                str(exc),
            )
            return {
                "answer": answer,
                "tool_context": answer,
                "reasoning_trace": state["reasoning_trace"]
                + [f"Review branch failed for {branch}."],
            }

        answer = self._format_review_answer(review)
        logger.info(
            "graph_node.review_branch.done conversation_id=%s branch=%r findings=%s",
            state["conversation_id"],
            branch,
            len(review.findings),
        )
        return {
            "answer": answer,
            "tool_context": answer,
            "reasoning_trace": state["reasoning_trace"]
            + [f"Review branch completed for {branch}."],
        }

    def _format_review_answer(self, review) -> str:
        lines = [
            f"Branch review against {review.base_branch}: {review.branch}",
            f"Base sync: {review.base_sync_id}",
            f"Head sync: {review.head_sync_id}",
            "",
            review.summary,
        ]

        if not review.findings:
            lines.extend(["", "No review findings detected."])
            return "\n".join(lines)

        lines.append("")
        lines.append("Findings:")
        for finding in review.findings:
            location = finding.path
            if finding.line_start is not None:
                if (
                    finding.line_end is not None
                    and finding.line_end != finding.line_start
                ):
                    location += f":{finding.line_start}-{finding.line_end}"
                else:
                    location += f":{finding.line_start}"
            lines.append(f"- [{finding.severity}] {finding.title} ({location})")
            lines.append(f"  {finding.rationale}")

        return "\n".join(lines)
