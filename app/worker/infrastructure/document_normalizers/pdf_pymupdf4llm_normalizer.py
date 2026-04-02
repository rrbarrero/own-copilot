from importlib import import_module
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from app.worker.domain.document_chunking_context import DocumentChunkingContext
from app.worker.domain.document_normalizer_proto import DocumentNormalizerProto


class PdfPyMuPDF4LLMNormalizer(DocumentNormalizerProto):
    def supports(self, context: DocumentChunkingContext) -> bool:
        extension = (context.extension or "").lower().lstrip(".")
        mime_type = (context.mime_type or "").lower()
        return extension == "pdf" or mime_type == "application/pdf"

    def normalize(
        self, content: bytes, context: DocumentChunkingContext
    ) -> dict[str, Any]:
        try:
            module = import_module("langchain_pymupdf4llm")
        except ImportError as exc:
            raise RuntimeError(
                "PDF support requires the 'langchain-pymupdf4llm' package."
            ) from exc

        loader_cls = module.PyMuPDF4LLMLoader

        suffix = Path(context.filename or "document.pdf").suffix or ".pdf"
        temp_path = ""
        try:
            with NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                temp_file.write(content)
                temp_path = temp_file.name

            loader = loader_cls(temp_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs if doc.page_content)

            return {
                "text": text,
                "format": "markdown",
                "metadata": {
                    "page_count": len(docs),
                    "source_format": "pdf",
                },
            }
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)
