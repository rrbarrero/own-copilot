from enum import StrEnum

from app.ingestion.domain.document import DocumentType


class FileValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AllowedExtension(StrEnum):
    MD = "md"
    TXT = "txt"
    JSON = "json"
    YML = "yml"
    YAML = "yaml"
    PY = "py"
    TS = "ts"
    GO = "go"

    @classmethod
    def get_doc_type(cls, ext: str) -> DocumentType:
        ext_map = {
            cls.MD: DocumentType.MARKDOWN,
            cls.TXT: DocumentType.TEXT,
            cls.JSON: DocumentType.CONFIG,
            cls.YML: DocumentType.CONFIG,
            cls.YAML: DocumentType.CONFIG,
            cls.PY: DocumentType.CODE,
            cls.TS: DocumentType.CODE,
            cls.GO: DocumentType.CODE,
        }
        return ext_map[cls(ext)]


class FileValidator:
    MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB
    MAX_FILES = 10

    @classmethod
    def validate_count(cls, count: int) -> None:
        if count > cls.MAX_FILES:
            raise FileValidationError(f"Maximum {cls.MAX_FILES} files allowed.")

    @classmethod
    def validate_file(cls, filename: str, content: bytes) -> str:
        # Extension validation
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        try:
            AllowedExtension(ext)
        except ValueError:
            allowed = [e.value for e in AllowedExtension]
            raise FileValidationError(
                f"File {filename} extension '{ext}' not allowed. Allowed: {allowed}"
            ) from None

        # Size validation
        if len(content) > cls.MAX_FILE_SIZE:
            raise FileValidationError(f"File {filename} exceeds 1MB limit.")

        return ext
