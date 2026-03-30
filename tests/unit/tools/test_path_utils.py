import pytest

from app.tools.domain.errors import InvalidRepositoryPathError
from app.tools.domain.path_utils import resolve_safe_path


def test_resolve_safe_path_keeps_paths_inside_root(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    nested = root / "src" / "main.py"
    nested.parent.mkdir()

    resolved = resolve_safe_path(str(root), "src/main.py")

    assert resolved == str(nested)


def test_resolve_safe_path_rejects_prefix_escape(tmp_path):
    root = tmp_path / "repo"
    sibling = tmp_path / "repo-evil"
    root.mkdir()
    sibling.mkdir()

    with pytest.raises(InvalidRepositoryPathError):
        resolve_safe_path(str(root), "../repo-evil/secret.txt")


def test_resolve_safe_path_rejects_symlink_escape(tmp_path):
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    link = root / "link"
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(InvalidRepositoryPathError):
        resolve_safe_path(str(root), "link/secret.txt")
