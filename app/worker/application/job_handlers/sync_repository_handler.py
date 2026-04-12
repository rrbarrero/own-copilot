import logging
import uuid
from datetime import UTC, datetime

from app.ingestion.domain.document import Document, DocumentStatus, SourceType
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.domain.job import Job
from app.ingestion.domain.storage_repo_proto import StorageRepoProto
from app.repositories.domain.git_repository_service_proto import (
    GitRepositoryServiceProto,
)
from app.repositories.domain.repository_repo_proto import RepositoryRepoProto
from app.repositories.domain.repository_sync import RepositorySync, RepositorySyncStatus
from app.repositories.domain.repository_sync_repo_proto import RepositorySyncRepoProto
from app.repositories.infra.repository_scanner import RepositoryScanner
from app.worker.application.document_processing_service import (
    DocumentProcessingService,
)
from app.worker.application.job_handler_proto import JobHandlerProto

logger = logging.getLogger(__name__)


class SyncRepositoryJobHandler(JobHandlerProto):
    """
    Handler for repository synchronization jobs.
    Orchestrates cloning, scanning, reconciliation, and indexing.
    """

    def __init__(
        self,
        repository_repo: RepositoryRepoProto,
        sync_repo: RepositorySyncRepoProto,
        git_service: GitRepositoryServiceProto,
        scanner: RepositoryScanner,
        document_repo: DocumentRepoProto,
        storage_repo: StorageRepoProto,
        processing_service: DocumentProcessingService,
    ):
        self._repository_repo = repository_repo
        self._sync_repo = sync_repo
        self._git_service = git_service
        self._scanner = scanner
        self._document_repo = document_repo
        self._storage_repo = storage_repo
        self._processing_service = processing_service

    async def handle(self, job: Job) -> None:
        repository_id = job.payload.get("repository_id")
        if not repository_id:
            raise ValueError(f"Job {job.id} does not contain 'repository_id'.")

        repo = await self._repository_repo.get_by_id(uuid.UUID(str(repository_id)))
        if not repo:
            raise ValueError(f"Repository {repository_id} not found.")

        # 1. Checkout repository
        branch = job.payload.get("branch") or repo.default_branch or "main"
        checkout_info = await self._git_service.ensure_checkout(repo, branch)
        resolved_branch = checkout_info.branch

        # 2. Create RepositorySync record
        sync = RepositorySync(
            id=uuid.uuid4(),
            repository_id=repo.id,
            branch=resolved_branch,
            commit_sha=checkout_info.commit_sha,
            status=RepositorySyncStatus.RUNNING,
            started_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await self._sync_repo.save(sync)

        try:
            # 3. Scan and reconcile
            scanned_files = list(self._scanner.scan(checkout_info.local_path))
            sync.scanned_files = len(scanned_files)

            seen_doc_uuids = set()
            branch_docs = await self._document_repo.list_by_repository_and_branch(
                repo.id, resolved_branch
            )
            branch_docs_by_source = {doc.source_id: doc for doc in branch_docs}

            for scanned_file in scanned_files:
                # 4. Find existing document
                doc = branch_docs_by_source.get(scanned_file.relative_path)

                # 5. Materialize the full snapshot in storage for this sync
                snapshot_path = (
                    f"repositories/{repo.id}/{sync.id}/{scanned_file.relative_path}"
                )
                with open(scanned_file.absolute_path, "rb") as f:
                    content_bytes = f.read()

                await self._storage_repo.save(snapshot_path, content_bytes)

                # 6. Determine if it needs re-indexing
                is_new = doc is None
                is_changed = (
                    doc is not None and doc.content_hash != scanned_file.content_hash
                )

                if is_new or is_changed:
                    if doc is None:
                        # Counting new as changed for simplicity
                        sync.changed_files += 1
                        doc = Document(
                            uuid=uuid.uuid4(),
                            source_type=SourceType.REPOSITORY,
                            source_id=scanned_file.relative_path,
                            path="",  # Updated below
                            filename=scanned_file.filename,
                            extension=scanned_file.extension,
                            doc_type=scanned_file.doc_type,
                            processing_status=DocumentStatus.QUEUED,
                            size_bytes=scanned_file.size_bytes,
                            created_at=datetime.now(UTC),
                            updated_at=datetime.now(UTC),
                            language=scanned_file.language,
                            repository_id=repo.id,
                            repository_url=repo.clone_url,
                            branch=resolved_branch,
                            content_hash=scanned_file.content_hash,
                            repository_sync_id=sync.id,
                        )
                    else:
                        sync.changed_files += 1
                        doc.content_hash = scanned_file.content_hash
                        doc.size_bytes = scanned_file.size_bytes
                        doc.updated_at = datetime.now(UTC)
                        doc.language = scanned_file.language
                        # Reset to pending for re-indexing
                        doc.processing_status = DocumentStatus.QUEUED
                        doc.repository_sync_id = sync.id
                        doc.branch = resolved_branch
                    doc.path = snapshot_path

                    await self._document_repo.save(doc)

                    # 7. Process (index) document
                    await self._processing_service.process(
                        doc.uuid, correlation_id=sync.id
                    )
                elif doc is not None:
                    doc.path = snapshot_path
                    doc.repository_sync_id = sync.id
                    doc.updated_at = datetime.now(UTC)
                    await self._document_repo.save(doc)

                if doc:
                    seen_doc_uuids.add(doc.uuid)

            # 8. Mark for deletion documents not seen in this branch sync
            for old_doc in branch_docs:
                if old_doc.uuid not in seen_doc_uuids:
                    await self._document_repo.delete_by_uuids([old_doc.uuid])
                    sync.deleted_files += 1

            # 9. Mark sync as completed
            sync.status = RepositorySyncStatus.COMPLETED
            sync.finished_at = datetime.now(UTC)
            sync.updated_at = datetime.now(UTC)
            await self._sync_repo.save(sync)

            # 10. Update repository last_synced_at
            repo.last_synced_at = datetime.now(UTC)
            repo.updated_at = datetime.now(UTC)
            await self._repository_repo.save(repo)

        except Exception as e:
            logger.error(f"Sync failed for repository {repo.id}: {e}")
            sync.status = RepositorySyncStatus.FAILED
            sync.last_error = str(e)
            sync.finished_at = datetime.now(UTC)
            sync.updated_at = datetime.now(UTC)
            await self._sync_repo.save(sync)
            raise e
