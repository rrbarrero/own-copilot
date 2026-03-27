from fastapi import FastAPI

from app.factory import create_llm
from app.ingestion.infra.endpoints import router as ingestion_router

app = FastAPI(title="Own Copilot API")

app.include_router(ingestion_router)


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
