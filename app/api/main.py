from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI

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
from app.repositories.domain.repository_repo_proto import RepositoryRepoProto
from app.repositories.infra.endpoints import router as repository_router
from app.schemas.chat import ChatRequest, ChatResponse
from app.tools.infra.endpoints import router as tools_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup: open the pool
    pool = Database.get_pool()
    await pool.open()

    # Proactive LLM & Chat service initialization (early warming)
    create_llm()
    create_chat_with_citations()

    yield
    # Shutdown: close the pool
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
    return await service.chat(request)
