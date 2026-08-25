import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from functools import partial

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.a2a.registry import AGENTS
from app.audit.recorder import audit_recorder
from app.graph.basic_graph import basic_graph
from app.rag.knowledge import DuplicateDocumentError, knowledge_service
from app.schemas.agent import AgentRunRequest, AgentRunResponse
from app.schemas.knowledge import DocumentCreateRequest, DocumentSummary

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent-runtime"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "UP", "service": "agent-runtime"}


async def _record_call(*, request: AgentRunRequest, status: str, node_count: int, started: float) -> None:
    """审计记录：异步执行，失败只告警，绝不影响主链路。"""
    try:
        await asyncio.to_thread(
            partial(
                audit_recorder.record,
                conversation_id=request.conversation_id,
                agent_type=request.agent_type,
                tenant_id=request.tenant_id or "",
                message=request.message,
                status=status,
                node_count=node_count,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        )
    except Exception as exc:
        logger.warning("调用审计记录失败: %s", exc)


@router.get("/agents/catalog")
async def list_agent_catalog() -> list[dict[str, object]]:
    """返回 A2A 智能体注册目录（客服入口 + 专业智能体）。"""
    return [
        {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "description": agent.description,
            "node": agent.node,
            "tools": list(agent.tools),
        }
        for agent in AGENTS.values()
    ]

@router.post("/agents/run", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    """执行 LangGraph 状态机；结束后异步写入调用审计。"""
    started = time.monotonic()
    result = await basic_graph.ainvoke(
        {
            "agent_type": request.agent_type,
            "conversation_id": request.conversation_id,
            "tenant_id": request.tenant_id,
            "user_message": request.message,
        },
        config={"configurable": {"thread_id": request.conversation_id}},
    )
    plan_len = len(result.get("plan") or [])
    node_count = plan_len + (4 if plan_len > 1 else 3)
    await _record_call(request=request, status=result["status"], node_count=node_count, started=started)
    return AgentRunResponse(
        conversation_id=request.conversation_id,
        agent_type=request.agent_type,
        status=result["status"],
        answer=result["answer"],
    )


@router.post("/agents/stream")
async def stream_agent(request: AgentRunRequest) -> EventSourceResponse:
    async def events() -> AsyncIterator[dict[str, str]]:
        started = time.monotonic()
        node_count = 0
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
                node_count += 1
                if isinstance(node_state, dict):
                    final_state.update(node_state)
                yield {
                    "event": "node",
                    "data": json.dumps({"node": node_name, "state": node_state}, ensure_ascii=False),
                }
        status = final_state.get("status", "COMPLETED")
        answer = final_state.get("answer", "")
        yield {
            "event": "done",
            "data": json.dumps({
                "conversation_id": request.conversation_id,
                "status": status,
                "answer": answer,
            }, ensure_ascii=False),
        }
        await _record_call(request=request, status=str(status), node_count=node_count, started=started)

    return EventSourceResponse(events())


@router.get("/audit/calls")
async def list_audit_calls(limit: int = 50, agent_type: str | None = None, status: str | None = None, tenant_id: str | None = None) -> list[dict[str, object]]:
    """查询调用审计记录；DB 不可用时返回空列表，不影响其它接口。"""
    try:
        return await asyncio.to_thread(
            partial(
                audit_recorder.list,
                limit=min(max(limit, 1), 200),
                agent_type=agent_type or None,
                status=status or None,
                tenant_id=tenant_id or None,
            )
        )
    except Exception as exc:
        logger.warning("调用审计查询失败: %s", exc)
        return []


@router.post("/knowledge/documents", status_code=201)
async def add_document(request: DocumentCreateRequest) -> dict[str, object]:
    """新增知识文档：切片后进入检索器并登记文档清单。"""
    try:
        chunk_ids = knowledge_service.add_document(
            request.document_id, request.content, tenant_id=request.tenant_id
        )
    except DuplicateDocumentError:
        raise HTTPException(status_code=409, detail=f"document_id already exists: {request.document_id}")
    return {
        "document_id": request.document_id,
        "tenant_id": request.tenant_id,
        "chunk_count": len(chunk_ids),
    }


@router.get("/knowledge/documents", response_model=list[DocumentSummary])
async def list_documents(tenant_id: str | None = None) -> list[dict[str, object]]:
    """返回知识库文档清单。"""
    return knowledge_service.list_documents(tenant_id=tenant_id)
