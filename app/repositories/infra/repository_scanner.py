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
    language: str | None = None


class RepositoryScanner:
    ALLOWED_EXTENSIONS = {
        "md": DocumentType.MARKDOWN,
        "txt": DocumentType.TEXT,
        "pdf": DocumentType.PDF,
        "toml": DocumentType.CONFIG,
        "json": DocumentType.CONFIG,
        "yml": DocumentType.CONFIG,
        "yaml": DocumentType.CONFIG,
        "py": DocumentType.CODE,
        "ts": DocumentType.CODE,
        "go": DocumentType.CODE,
        "python-version": DocumentType.CONFIG,
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
                extension = self._extract_extension(file_path)

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
                        language=self._infer_language(extension),
                        size_bytes=size_bytes,
                        doc_type=self.ALLOWED_EXTENSIONS[extension],
                        content_hash=content_hash,
                    )

    @staticmethod
    def _extract_extension(file_path: Path) -> str:
        # Dotfiles like `.python-version` need to be treated as config files,
        # not as "extensionless" files.
        if file_path.name.startswith(".") and file_path.suffix == "":
            return file_path.name.lstrip(".").lower()
        return file_path.suffix.lower().lstrip(".")

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculates SHA256 of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _infer_language(extension: str) -> str | None:
        return {
            "py": "python",
            "ts": "typescript",
            "go": "go",
            "md": "markdown",
        }.get(extension)
