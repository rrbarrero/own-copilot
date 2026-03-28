from app.retrieval.domain.retrieved_chunk import RetrievedChunk
from app.schemas.chat import ChatCitation


class ContextBuilder:
    def build_context(
        self,
        chunks: list[RetrievedChunk],
    ) -> tuple[str, list[ChatCitation]]:
        if not chunks:
            return "", []

        context_parts = []
        citations = []

        for i, chunk in enumerate(chunks):
            # Format each chunk in a clear way for the prompt
            context_parts.append(
                f"[Document {i + 1}]\nSource: {chunk.path}\nContent:\n{chunk.content}"
            )

            # Build the citation
            citations.append(
                ChatCitation(
                    document_id=chunk.document_uuid,
                    path=chunk.path,
                    filename=chunk.filename,
                    chunk_index=chunk.chunk_index,
                )
            )

        context_str = "\n\n---\n\n".join(context_parts)
        return context_str, citations
