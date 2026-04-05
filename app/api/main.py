import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI

from app.config import settings
from app.conversation.application.chat_service import ChatService
from app.factory import (
    create_chat_service,
    create_chat_with_citations,
    create_document_repo,
    create_llm,
    create_repository_repo,
)
from app.infra.db import Database
from app.ingestion.domain.document_repo_proto import DocumentRepoProto
from app.ingestion.infra.endpoints import router as ingestion_router
from app.logging_utils import configure_logging
from app.repositories.domain.repository_repo_proto import RepositoryRepoProto
from app.repositories.infra.endpoints import router as repository_router
from app.schemas.chat import ChatRequest, ChatResponse
from app.tools.infra.endpoints import router as tools_router

configure_logging("api")
logging.getLogger("app").setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup: open the pool
    logger.info("api.startup opening database pool")
    pool = Database.get_pool()
    await pool.open()

    # Proactive LLM & Chat service initialization (early warming)
    create_llm()
    create_chat_with_citations()
    logger.info("api.startup services warmed")

    yield
    # Shutdown: close the pool
    logger.info("api.shutdown closing database pool")
    await Database.close()


app = FastAPI(title="Own Copilot API", lifespan=lifespan)

app.include_router(ingestion_router)
app.include_router(repository_router)
app.include_router(tools_router)


@app.get("/")
async def root():
    return {"message": "Own Copilot API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/repositories")
async def list_repositories(
    repo: Annotated[RepositoryRepoProto, Depends(create_repository_repo)],
):
    repos = await repo.list_all()
    return [{"id": r.id, "name": r.name, "owner": r.owner} for r in repos]


@app.get("/documents")
async def list_documents(
    repo: Annotated[DocumentRepoProto, Depends(create_document_repo)],
):
    docs = await repo.list_all()
    return [{"id": d.uuid, "filename": d.filename} for d in docs]


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[ChatService, Depends(create_chat_service)],
):
    logger.info(
        "api.chat.request scope_type=%s repository_id=%s document_id=%s "
        "conversation_id=%s question=%r",
        request.scope.type,
        request.scope.repository_id,
        request.scope.document_id,
        request.conversation_id,
        request.question,
    )
    response = await service.chat(request)
    logger.info(
        "api.chat.response conversation_id=%s citations=%s answer_preview=%r",
        response.conversation_id,
        len(response.citations),
        response.answer[:200],
    )
    return response
