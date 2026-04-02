import sys
import types

from app.worker.domain.document_chunking_context import DocumentChunkingContext
from app.worker.infrastructure.document_normalizers.pdf_pymupdf4llm_normalizer import (
    PdfPyMuPDF4LLMNormalizer,
)


def test_pdf_normalizer_supports_pdf_extension():
    normalizer = PdfPyMuPDF4LLMNormalizer()

    assert normalizer.supports(DocumentChunkingContext(extension="pdf"))
    assert normalizer.supports(
        DocumentChunkingContext(extension=None, mime_type="application/pdf")
    )
    assert not normalizer.supports(DocumentChunkingContext(extension="txt"))


def test_pdf_normalizer_returns_markdown(monkeypatch):
    class FakeDoc:
        def __init__(self, page_content: str):
            self.page_content = page_content

    class FakeLoader:
        def __init__(self, path: str):  # noqa: ARG002
            pass

        def load(self):
            return [FakeDoc("# Title"), FakeDoc("## Section")]

    fake_module = types.SimpleNamespace(PyMuPDF4LLMLoader=FakeLoader)
    monkeypatch.setitem(sys.modules, "langchain_pymupdf4llm", fake_module)

    normalizer = PdfPyMuPDF4LLMNormalizer()
    result = normalizer.normalize(
        b"%PDF-1.7 fake bytes",
        DocumentChunkingContext(filename="paper.pdf", extension="pdf"),
    )

    assert result["format"] == "markdown"
    assert result["metadata"]["page_count"] == 2
    assert "# Title" in result["text"]
    assert "## Section" in result["text"]
