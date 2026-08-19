from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(
    title="Huizhitong Agent Runtime",
    version="0.1.0",
    description="LangGraph Agent、RAG 与 MCP 的统一运行时入口",
)
app.include_router(router, prefix="/internal")

