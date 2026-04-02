import pytest

from app.ingestion.domain.document import DocumentType
from app.ingestion.domain.file_validator import (
    AllowedExtension,
    FileValidationError,
    FileValidator,
)


def test_validate_toml_file():
    ext = FileValidator.validate_file("pyproject.toml", b"[project]\nname='test'\n")
    assert ext == "toml"
    assert AllowedExtension.get_doc_type(ext) == DocumentType.CONFIG


def test_validate_python_version_dotfile():
    ext = FileValidator.validate_file(".python-version", b"3.13\n")
    assert ext == "python-version"
    assert AllowedExtension.get_doc_type(ext) == DocumentType.CONFIG


def test_validate_pdf_file():
    ext = FileValidator.validate_file("paper.pdf", b"%PDF-1.7")
    assert ext == "pdf"
    assert AllowedExtension.get_doc_type(ext) == DocumentType.PDF


def test_reject_unknown_extension():
    with pytest.raises(FileValidationError, match="extension 'ini' not allowed"):
        FileValidator.validate_file("settings.ini", b"[x]\n")
