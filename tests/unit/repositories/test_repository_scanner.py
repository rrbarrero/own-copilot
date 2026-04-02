from pathlib import Path

from app.ingestion.domain.document import DocumentType
from app.repositories.infra.repository_scanner import RepositoryScanner


def test_extract_extension_for_toml_file():
    ext = RepositoryScanner._extract_extension(Path("pyproject.toml"))
    assert ext == "toml"


def test_extract_extension_for_python_version_dotfile():
    ext = RepositoryScanner._extract_extension(Path(".python-version"))
    assert ext == "python-version"


def test_scan_includes_toml_and_python_version(tmp_path: Path):
    scanner = RepositoryScanner()

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname='demo'\n")

    python_version = tmp_path / ".python-version"
    python_version.write_text("3.13\n")

    scanned = list(scanner.scan(str(tmp_path)))
    by_name = {item.filename: item for item in scanned}

    assert "pyproject.toml" in by_name
    assert by_name["pyproject.toml"].extension == "toml"
    assert by_name["pyproject.toml"].doc_type == DocumentType.CONFIG

    assert ".python-version" in by_name
    assert by_name[".python-version"].extension == "python-version"
    assert by_name[".python-version"].doc_type == DocumentType.CONFIG
