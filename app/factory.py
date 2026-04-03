from functools import lru_cache

from app.agentic.application.graph_chat_service import GraphChatService
from app.agentic.application.nodes.answer_from_context import (
    AnswerFromContextNode,
)
from app.agentic.application.nodes.decide_next_action import (
    DecideNextActionNode,
)
from app.agentic.application.nodes.evaluate_evidence import (
    EvaluateEvidenceNode,
)
from app.agentic.application.nodes.rewrite_question import RewriteQuestionNode
from app.agentic.application.nodes.run_find_files import RunFindFilesNode
from app.agentic.application.nodes.run_rag import RunRagNode
from app.agentic.application.nodes.run_read_file import RunReadFileNode
from app.agentic.application.nodes.run_search_in_repo import (
    RunSearchInRepoNode,
)
from app.agentic.application.nodes.stop_no_evidence import StopNoEvidenceNode
from app.agentic.infra.langgraph_builder import LangGraphBuilder
from app.config import settings
from app.conversation.application.question_rewriter import QuestionRewriter
from app.conversation.domain.conversation_repo_proto import ConversationRepoProto
from app.conversation.infra.postgres_conversation_repo import (
    PostgresConversationRepo,
)
from app.core.llm import get_llm
from app.infra.db import Database
from app.ingestion.application.ingestion_service import IngestionService
from app.ingestion.domain.chunk_repo_proto import ChunkRepoProto
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.domain.job_repo_proto import JobRepoProto
from app.ingestion.domain.storage_repo_proto import StorageRepoProto
from app.ingestion.infra.in_filesystem_storage_repo import InFilesystemStorageRepo
from app.ingestion.infra.postgres_chunk_repo import PostgresChunkRepo
from app.ingestion.infra.postgres_document_repo import PostgresDocumentRepo
from app.ingestion.infra.postgres_job_repo import PostgresJobRepo
from app.repositories.application.request_repository_sync import (
    RequestRepositorySync,
)
from app.repositories.domain.repository_repo_proto import RepositoryRepoProto
from app.repositories.domain.repository_sync_repo_proto import (
    RepositorySyncRepoProto,
)
from app.repositories.infra.postgres_repository_repo import (
    PostgresRepositoryRepo,
)
from app.repositories.infra.postgres_repository_sync_repo import (
    PostgresRepositorySyncRepo,
)
from app.repositories.infra.repository_url_normalizer import (
    RepositoryUrlNormalizer,
)
from app.retrieval.application.chat_with_citations import ChatWithCitations
from app.retrieval.application.retriever import Retriever
from app.retrieval.infra.hybrid_retrieval_service import HybridRetrievalService
from app.retrieval.infra.ollama_query_embedding_service import (
    OllamaQueryEmbeddingService,
)
from app.retrieval.infra.postgres_lexical_retrieval_provider import (
    PostgresLexicalRetrievalProvider,
)
from app.retrieval.infra.postgres_vector_retrieval_provider import (
    PostgresVectorRetrievalProvider,
)
from app.retrieval.infra.rrf_rank_fuser import RRFRankFuser
from app.tools.application.find_files import FindFiles
from app.tools.application.read_file import ReadFile
from app.tools.application.repository_tool_service import RepositoryToolService
from app.tools.application.search_in_repo import SearchInRepo
from app.tools.infra.filesystem_repository_snapshot_resolver import (
    FilesystemRepositorySnapshotResolver,
)


@lru_cache
def create_llm():
    return get_llm()


def create_document_repo() -> DocumentRepoProto:
    return PostgresDocumentRepo(Database.get_pool())


def create_chunk_repo() -> ChunkRepoProto:
    return PostgresChunkRepo(Database.get_pool())


def create_storage_repo() -> StorageRepoProto:
    return InFilesystemStorageRepo(settings.STORAGE_PATH)


def create_job_repo() -> JobRepoProto:
    return PostgresJobRepo(Database.get_pool())


def create_repository_repo() -> RepositoryRepoProto:
    return PostgresRepositoryRepo(Database.get_pool())


def create_repository_sync_repo() -> RepositorySyncRepoProto:
    return PostgresRepositorySyncRepo(Database.get_pool())


def create_request_repository_sync() -> RequestRepositorySync:
    return RequestRepositorySync(
        repository_repo=create_repository_repo(),
        job_repo=create_job_repo(),
        url_normalizer=RepositoryUrlNormalizer(),
        # Use STORAGE_PATH/checkouts for git roots
        checkouts_root=f"{settings.STORAGE_PATH}/checkouts",
    )


def create_ingestion_service() -> IngestionService:
    return IngestionService(
        doc_repo=create_document_repo(),
        storage_repo=create_storage_repo(),
        job_repo=create_job_repo(),
    )


def create_retrieval_repo():
    return HybridRetrievalService(
        vector_provider=PostgresVectorRetrievalProvider(Database.get_pool()),
        lexical_provider=PostgresLexicalRetrievalProvider(Database.get_pool()),
        rank_fuser=RRFRankFuser(),
    )


@lru_cache
def create_query_embedding_service():
    return OllamaQueryEmbeddingService(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )


@lru_cache
def create_retriever():
    return Retriever(
        retrieval_repo=create_retrieval_repo(),
        embedding_service=create_query_embedding_service(),
        threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD,
        fallback_threshold=settings.RETRIEVAL_FALLBACK_THRESHOLD,
    )


@lru_cache
def create_chat_with_citations():
    return ChatWithCitations(
        retriever=create_retriever(),
        llm=create_llm(),
    )


def create_conversation_repo() -> ConversationRepoProto:
    return PostgresConversationRepo(Database.get_pool())


@lru_cache
def create_question_rewriter():
    return QuestionRewriter(llm=create_llm())


@lru_cache
def create_langgraph():
    llm = create_llm()
    tool_service = create_repository_tool_service()

    builder = LangGraphBuilder(
        rewrite_node=RewriteQuestionNode(create_question_rewriter()),
        decide_node=DecideNextActionNode(llm),
        rag_node=RunRagNode(create_retriever()),
        find_files_node=RunFindFilesNode(tool_service),
        read_file_node=RunReadFileNode(tool_service),
        search_in_repo_node=RunSearchInRepoNode(tool_service),
        evaluate_node=EvaluateEvidenceNode(),
        answer_node=AnswerFromContextNode(llm),
        stop_no_evidence_node=StopNoEvidenceNode(),
    )
    return builder.build()


@lru_cache
def create_chat_service():
    return GraphChatService(
        conversation_repo=create_conversation_repo(),
        graph=create_langgraph(),
        history_limit=settings.CONVERSATION_HISTORY_LIMIT,
    )


def create_repository_snapshot_resolver():
    return FilesystemRepositorySnapshotResolver(
        repository_repo=create_repository_repo(),
        sync_repo=create_repository_sync_repo(),
        storage_path=settings.STORAGE_PATH,
    )


@lru_cache
def create_repository_tool_service():
    resolver = create_repository_snapshot_resolver()
    return RepositoryToolService(
        find_files=FindFiles(resolver),
        read_file=ReadFile(resolver),
        search_in_repo=SearchInRepo(resolver),
    )
