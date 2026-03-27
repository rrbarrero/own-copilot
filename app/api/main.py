from fastapi import FastAPI

from app.factory import create_llm

app = FastAPI(title="Own Copilot API")


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
