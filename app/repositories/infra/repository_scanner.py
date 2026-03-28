import hashlib
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.domain.document import DocumentType


@dataclass
class ScannedRepositoryFile:
    relative_path: str
    absolute_path: str
    filename: str
    extension: str
    size_bytes: int
    doc_type: DocumentType
    content_hash: str


class RepositoryScanner:
    ALLOWED_EXTENSIONS = {
        "md": DocumentType.MARKDOWN,
        "txt": DocumentType.TEXT,
        "json": DocumentType.CONFIG,
        "yml": DocumentType.CONFIG,
        "yaml": DocumentType.CONFIG,
        "py": DocumentType.CODE,
        "ts": DocumentType.CODE,
        "go": DocumentType.CODE,
    }

    EXCLUDED_DIRS = {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
    }

    def scan(self, root_path: str) -> Iterator[ScannedRepositoryFile]:
        """
        Scans a directory for relevant files based on internal whitelist.
        Calculates SHA256 hashes of contents for change detection.
        """
        root = Path(root_path)

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune excluded directories
            dirnames[:] = [d for d in dirnames if d not in self.EXCLUDED_DIRS]

            for filename in filenames:
                file_path = Path(dirpath) / filename
                extension = file_path.suffix.lower().lstrip(".")

                if extension in self.ALLOWED_EXTENSIONS:
                    relative_path = str(file_path.relative_to(root))
                    size_bytes = file_path.stat().st_size

                    if size_bytes > 1_000_000:  # 1MB limit from plan
                        continue

                    content_hash = self._calculate_hash(file_path)

                    yield ScannedRepositoryFile(
                        relative_path=relative_path,
                        absolute_path=str(file_path),
                        filename=filename,
                        extension=extension,
                        size_bytes=size_bytes,
                        doc_type=self.ALLOWED_EXTENSIONS[extension],
                        content_hash=content_hash,
                    )

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculates SHA256 of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
