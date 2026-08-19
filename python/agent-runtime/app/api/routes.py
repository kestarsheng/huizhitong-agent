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
    result = await basic_graph.ainvoke({
        "agent_type": request.agent_type,
        "conversation_id": request.conversation_id,
        "tenant_id": request.tenant_id,
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
        yield {"event": "accepted", "data": json.dumps({"agent_type": request.agent_type}, ensure_ascii=False)}
        graph_input = {
            "agent_type": request.agent_type,
            "conversation_id": request.conversation_id,
            "tenant_id": request.tenant_id,
            "user_message": request.message,
        }
        config = {"configurable": {"thread_id": request.conversation_id}}
        final_state: dict[str, object] = {}
        async for update in basic_graph.astream(graph_input, config=config, stream_mode="updates"):
            for node_name, node_state in update.items():
                if isinstance(node_state, dict):
                    final_state.update(node_state)
                yield {
                    "event": "node",
                    "data": json.dumps({"node": node_name, "state": node_state}, ensure_ascii=False),
                }
        yield {
            "event": "done",
            "data": json.dumps({
                "conversation_id": request.conversation_id,
                "status": final_state.get("status", "COMPLETED"),
                "answer": final_state.get("answer", ""),
            }, ensure_ascii=False),
        }

    return EventSourceResponse(events())

