from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.factory import create_llm
from app.infra.db import Database
from app.ingestion.infra.endpoints import router as ingestion_router
from app.repositories.infra.endpoints import router as repository_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup: open the pool
    pool = Database.get_pool()
    await pool.open()
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


@app.post("/chat")
async def chat(query: str):
    llm = create_llm()
    response = await llm.ainvoke(query)
    return {"response": response.content}
