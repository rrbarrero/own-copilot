from uuid import UUID


class ToolError(Exception):
    """Base class for all tools related errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class RepositoryNotFoundError(ToolError):
    def __init__(self, repository_id: UUID):
        super().__init__(f"Repository {repository_id} not found.")


class RepositorySnapshotNotFoundError(ToolError):
    def __init__(self, repository_id: UUID):
        super().__init__(f"No completed snapshot found for repository {repository_id}.")


class InvalidRepositoryPathError(ToolError):
    def __init__(self, path: str):
        super().__init__(f"Invalid or insecure path: {path}")


class RepositoryFileNotFoundError(ToolError):
    def __init__(self, path: str):
        super().__init__(f"File not found in snapshot: {path}")


class RepositoryFileNotReadableError(ToolError):
    def __init__(self, path: str, reason: str):
        super().__init__(f"File {path} is not readable: {reason}")


class ToolInputValidationError(ToolError):
    pass
