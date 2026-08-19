from collections.abc import AsyncIterator
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.schemas.agent import AgentRunRequest, AgentRunResponse

router = APIRouter(tags=["agent-runtime"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP", "service": "agent-runtime"}


@router.post("/agents/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    """基础同步入口，后续由 LangGraph Runtime 替换执行逻辑。"""
    return AgentRunResponse(
        conversation_id=request.conversation_id,
        agent_type=request.agent_type,
        status="ACCEPTED",
        answer="Agent Runtime 已接收请求，编排引擎尚未接入。",
    )


@router.post("/agents/stream")
async def stream_agent(request: AgentRunRequest) -> EventSourceResponse:
    async def events() -> AsyncIterator[dict[str, str]]:
        yield {"event": "accepted", "data": json.dumps({"agent_type": request.agent_type})}
        yield {"event": "message", "data": "Agent Runtime 已接收请求"}
        yield {"event": "done", "data": "true"}

    return EventSourceResponse(events())

