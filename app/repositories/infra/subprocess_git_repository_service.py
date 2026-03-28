import asyncio
from pathlib import Path

from app.repositories.domain.git_repository_service_proto import (
    CheckoutInfo,
    GitRepositoryServiceProto,
)
from app.repositories.domain.repository import Repository


class SubprocessGitRepositoryService(GitRepositoryServiceProto):
    def __init__(self, checkouts_root: str):
        self.checkouts_root = Path(checkouts_root)
        self.checkouts_root.mkdir(parents=True, exist_ok=True)

    async def ensure_checkout(
        self, repository: Repository, branch: str | None = None
    ) -> CheckoutInfo:
        """
        Executes git commands via subprocess to manage a local checkout.
        """
        repo_dir = self.checkouts_root / f"{repository.owner}_{repository.name}"
        target_branch = branch or repository.default_branch or "main"

        if not repo_dir.exists():
            await self._run_git("clone", repository.clone_url, str(repo_dir))
        else:
            await self._run_git("-C", str(repo_dir), "fetch", "--all", "--prune")

        # Checkout and reset to head of origin
        await self._run_git("-C", str(repo_dir), "checkout", target_branch)
        await self._run_git(
            "-C", str(repo_dir), "reset", "--hard", f"origin/{target_branch}"
        )

        # Determine final commit SHA
        commit_sha = await self._run_git("-C", str(repo_dir), "rev-parse", "HEAD")

        return CheckoutInfo(
            local_path=str(repo_dir),
            branch=target_branch,
            commit_sha=commit_sha.strip(),
        )

    async def _run_git(self, *args: str) -> str:
        """Helper to run git commands asynchronously."""
        process = await asyncio.create_subprocess_exec(
            "git",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            raise RuntimeError(
                f"Git command failed: git {' '.join(args)}\nError: {error_msg}"
            )

        return stdout.decode().strip()
