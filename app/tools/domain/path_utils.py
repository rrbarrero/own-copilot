from pathlib import Path

from app.tools.domain.errors import InvalidRepositoryPathError


def resolve_safe_path(root_path: str, relative_path: str) -> str:
    """
    Resolves an absolute path within a root directory, ensuring that
    the requested path does not escape the root (preventing path traversal).
    """
    if not relative_path:
        return str(Path(root_path).resolve())

    requested_path = Path(relative_path)
    if requested_path.is_absolute() or requested_path.parts[0] == "..":
        raise InvalidRepositoryPathError(relative_path)

    abs_root = Path(root_path).resolve()
    abs_target = (abs_root / requested_path).resolve()

    if abs_target != abs_root and abs_root not in abs_target.parents:
        raise InvalidRepositoryPathError(relative_path)

    return str(abs_target)
