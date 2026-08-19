from collections.abc import AsyncIterator
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.graph.basic_graph import basic_graph

router = APIRouter(tags=["agent-runtime"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP", "service": "agent-runtime"}


@router.post("/agents/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    """执行基础 LangGraph 状态图，后续替换节点内部的模型和工具实现。"""
    result = basic_graph.invoke({
        "agent_type": request.agent_type,
        "conversation_id": request.conversation_id,
        "user_message": request.message,
    }, config={"configurable": {"thread_id": request.conversation_id}})
    return AgentRunResponse(
        conversation_id=request.conversation_id,
        agent_type=request.agent_type,
        status=result["status"],
        answer=result["answer"],
    )


@router.post("/agents/stream")
async def stream_agent(request: AgentRunRequest) -> EventSourceResponse:
    async def events() -> AsyncIterator[dict[str, str]]:
        yield {"event": "accepted", "data": json.dumps({"agent_type": request.agent_type})}
        yield {"event": "message", "data": "Agent Runtime 已接收请求"}
        yield {"event": "done", "data": "true"}

    return EventSourceResponse(events())

