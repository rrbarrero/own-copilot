import logging

from app.agentic.domain.graph_state import AgentGraphState
from app.retrieval.application.retriever import Retriever

logger = logging.getLogger(__name__)


class RunRagNode:
    """
    Executes a semantic retrieval (RAG) to gather context.
    """

    def __init__(self, retriever: Retriever):
        self._retriever = retriever

    async def __call__(self, state: AgentGraphState) -> dict:
        """
        Retrieves context semantically based on the rewritten question.
        """
        logger.info(
            "graph_node.run_rag conversation_id=%s question=%r",
            state["conversation_id"],
            state["rewritten_question"],
        )
        chunks = await self._retriever.retrieve(
            question=state["rewritten_question"], scope=state["scope"]
        )

        # Build context string
        context_items = []
        citations = state["citations"][:]  # Clone list

        for i, chunk in enumerate(chunks):
            # Enriched context prefix for RAPTOR summaries
            kind = chunk.metadata.get("chunk_kind", "raw")
            prefix = ""
            if kind == "summary":
                level = chunk.metadata.get("summary_level", "symbol")
                symbol_name = chunk.metadata.get("symbol_name", "")
                prefix = f"[SUMMARY {level.upper()} {symbol_name}] "

            context_items.append(f"[{i + 1}] {prefix}{chunk.content}")
            citations.append(
                {
                    "document_id": chunk.document_uuid,
                    "path": chunk.path,
                    "filename": chunk.filename,
                    "chunk_index": self._resolve_citation_chunk_index(chunk),
                }
            )

        retrieved_context = "\n\n".join(context_items) if context_items else ""

        logger.info(
            "graph_node.run_rag.done conversation_id=%s chunks=%s citations=%s",
            state["conversation_id"],
            len(chunks),
            len(citations),
        )

        return {
            "retrieved_context": retrieved_context,
            "citations": citations,
            "reasoning_trace": state["reasoning_trace"]
            + [f"RAG executed. Obtained {len(chunks)} chunks."],
        }

    @staticmethod
    def _resolve_citation_chunk_index(chunk) -> int:  # noqa: ANN001
        if chunk.metadata.get("chunk_kind") != "summary":
            return chunk.chunk_index

        parent_chunk_indexes = chunk.metadata.get("parent_chunk_indexes", [])
        if parent_chunk_indexes:
            return int(parent_chunk_indexes[0])

        return chunk.chunk_index
