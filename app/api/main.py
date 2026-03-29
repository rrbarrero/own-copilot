from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI

from app.factory import create_chat_with_citations, create_llm
from app.infra.db import Database
from app.ingestion.infra.endpoints import router as ingestion_router
from app.repositories.infra.endpoints import router as repository_router
from app.retrieval.application.chat_with_citations import ChatWithCitations
from app.schemas.chat import ChatRequest, ChatResponse


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


@app.get("/")
async def root():
    return {"message": "Own Copilot API is running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    service: Annotated[ChatWithCitations, Depends(create_chat_with_citations)],
):
    return await service.chat(request)
