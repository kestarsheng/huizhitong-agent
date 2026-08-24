import logging
import os
import re

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.graph.state import RESET_MARKER, AgentState
from app.llm.gateway import generate_answer
from app.rag.knowledge import knowledge_service
from app.tools.inventory_gateway import inventory_gateway, mcp_inventory_gateway
from app.tools.registry_client import tool_registry_client
from app.tools.ticket_gateway import mcp_ticket_gateway, ticket_gateway

logger = logging.getLogger(__name__)

STEP_NODES = ("inventory", "knowledge", "ticket", "general")

_STATUS_SEVERITY = {
    "FORBIDDEN": 5,
    "NEED_INPUT": 4,
    "WAITING_RAG": 3,
    "COMPLETED": 2,
    "PLANNED": 1,
    "CLASSIFIED": 1,
}


def pick_worst_status(statuses: list[str]) -> str:
    """多分支结果取最需要用户关注的语义状态。"""
    if not statuses:
        return "COMPLETED"
    return max(statuses, key=lambda status: _STATUS_SEVERITY.get(status, 1))


def classify_intent(state: AgentState) -> AgentState:
    """意图识别：可识别多意图（库存+知识/工单），触发并行编排。"""
    message = state["user_message"]
    inventory_hit = any(word in message for word in ("库存", "商品", "销量"))
    ticket_hit = any(word in message for word in ("工单", "售后", "投诉", "报修"))
    knowledge_hit = any(word in message for word in ("故障", "维修", "手册", "怎么处理", "错误码")) or re.search(r"E-\d{3,}", message, re.IGNORECASE) is not None
    intents: list[str] = []
    if inventory_hit:
        intents.append("inventory")
    if ticket_hit:
        intents.append("ticket")
    elif knowledge_hit:
        intents.append("knowledge")
    if not intents:
        intents = ["general"]
    return {
        "intent": intents[0],
        "intents": intents,
        "status": "CLASSIFIED",
        "step_answers": [RESET_MARKER],
        "step_statuses": [RESET_MARKER],
    }


def plan_task(state: AgentState) -> AgentState:
    """任务规划：将意图列表转换为可执行的节点序列。"""
    intents = state.get("intents") or [state.get("intent") or "general"]
    plan = [item for item in intents if item in STEP_NODES]
    if not plan:
        plan = ["general"]
    return {"plan": plan, "status": "PLANNED"}


def route_plan(state: AgentState) -> str | list[Send]:
    """条件路由：单意图直接进入对应节点；多意图通过 Send 并行展开。"""
    plan = state.get("plan") or ["general"]
    if len(plan) == 1:
        return plan[0]
    return [Send(step, state) for step in plan]


async def inventory_node(state: AgentState) -> AgentState:
    if state.get("tenant_id") is not None:
        allowed = await tool_registry_client.available_tools(state.get("agent_type", "inventory"), state["tenant_id"])
        allowed_names = {item.get("toolName") for item in allowed}
        if allowed and not ({"query_inventory", "analyze_inventory_risk"} & allowed_names):
            return _step_result("当前租户未授权库存工具，请联系管理员开通。", "FORBIDDEN")
    product_id = re.search(r"P\d{4}", state["user_message"], re.IGNORECASE)
    if product_id is None:
        return _step_result("请提供商品编号，例如 P1001。", "NEED_INPUT")
    if os.getenv("MCP_INVENTORY_ENABLED", "false").lower() == "true":
        result = await mcp_inventory_gateway.analyze(product_id.group().upper())
    else:
        result = inventory_gateway.analyze(product_id.group().upper())
    if not result["found"]:
        return _step_result(result["message"], "COMPLETED")
    answer = (f"商品 {result['product_id']}（{result['product_name']}）当前库存 "
              f"{result['stock']}，安全库存 {result['safe_stock']}，风险等级 {result['risk']}；"
              f"{result['suggestion']}。")
    return _step_result(answer, "COMPLETED")


async def knowledge_node(state: AgentState) -> AgentState:
    context = knowledge_service.search_context(state["user_message"])
    if not context:
        return _step_result("知识库暂未检索到相关内容，请补充设备型号、错误码或具体故障现象。", "WAITING_RAG")
    return _step_result(f"根据知识库检索结果：\n{context}", "WAITING_RAG")


def _parse_ticket_priority(message: str) -> str:
    if any(word in message for word in ("紧急", "加急", "尽快", "马上")):
        return "HIGH"
    if any(word in message for word in ("一般", "普通", "咨询")):
        return "LOW"
    return "MEDIUM"


async def ticket_node(state: AgentState) -> AgentState:
    if state.get("tenant_id") is not None:
        allowed = await tool_registry_client.available_tools(state.get("agent_type", "ticket"), state["tenant_id"])
        allowed_names = {item.get("toolName") for item in allowed}
        if allowed and not ({"create_ticket", "query_ticket"} & allowed_names):
            return _step_result("当前租户未授权工单工具，请联系管理员开通。", "FORBIDDEN")
    message = state["user_message"]
    ticket_id_match = re.search(r"TK-\d{3,}", message, re.IGNORECASE)
    if ticket_id_match:
        ticket_id = ticket_id_match.group().upper()
        if os.getenv("MCP_TICKET_ENABLED", "false").lower() == "true":
            result = await mcp_ticket_gateway.query(ticket_id)
        else:
            result = ticket_gateway.query(ticket_id)
        if not result["found"]:
            return _step_result(result["message"], "COMPLETED")
        return _step_result(f"工单 {result['ticket_id']}（{result['subject']}）当前状态 {result['status']}，"
                            f"优先级 {result['priority']}。", "COMPLETED")
    subject = message[:30].strip()
    if os.getenv("MCP_TICKET_ENABLED", "false").lower() == "true":
        result = await mcp_ticket_gateway.create(subject, message, priority=_parse_ticket_priority(message))
    else:
        result = ticket_gateway.create(subject, message, priority=_parse_ticket_priority(message))
    if not result["created"]:
        return _step_result(result["message"], "COMPLETED")
    return _step_result(f"已创建工单 {result['ticket_id']}（{result['subject']}），优先级 {result['priority']}，"
                        f"当前状态 {result['status']}。", "COMPLETED")


async def general_node(state: AgentState) -> AgentState:
    answer = await generate_answer(
        "你是汇智通企业智能体助手。请简洁、准确地回答用户问题；无法确认时明确说明。",
        state["user_message"],
    )
    if answer is None:
        answer = "当前未启用可用的大模型（DeepSeek / 通义千问），请联系管理员配置 API Key。"
    return _step_result(answer, "COMPLETED")


def _step_result(answer: str, status: str) -> AgentState:
    """工具/模型节点统一输出：只写入累加器，避免并行分支冲突写 answer/status。

    最终 answer/status 由 validate_result 节点统一聚合产出。
    """
    return {
        "step_answers": [answer],
        "step_statuses": [status],
    }


def validate_result(state: AgentState) -> AgentState:
    """结果校验：聚合各分支答案，选取最需关注的语义状态作为最终状态。"""
    answers = state.get("step_answers") or []
    statuses = state.get("step_statuses") or []
    joined = "\n".join(answers) if answers else state.get("answer", "未获取到可回答的结果，请补充信息后重试。")
    return {"answer": joined, "status": pick_worst_status(statuses)}


def build_checkpointer():
    """Checkpoint 工厂：memory 默认；postgres/auto 配置 PG_DSN 后启用 PostgreSQL 持久化。

    PostgreSQL 不可用时自动降级 MemorySaver，保证链路始终可用。
    """
    mode = os.getenv("AGENT_CHECKPOINT", "memory").lower()
    dsn = os.getenv("PG_DSN", "")
    if mode in ("postgres", "auto") and dsn:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            saver = PostgresSaver.from_conn_string(dsn)
            saver.setup()
            logger.info("已启用 PostgreSQL checkpoint: %s", dsn)
            return saver
        except Exception as exc:
            logger.warning("PostgreSQL checkpoint 不可用，降级为 MemorySaver: %s", exc)
    return MemorySaver()


def build_basic_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("plan_task", plan_task)
    graph.add_node("inventory", inventory_node)
    graph.add_node("knowledge", knowledge_node)
    graph.add_node("ticket", ticket_node)
    graph.add_node("general", general_node)
    graph.add_node("validate_result", validate_result)
    graph.add_edge(START, "classify_intent")
    graph.add_edge("classify_intent", "plan_task")
    graph.add_conditional_edges("plan_task", route_plan, list(STEP_NODES))
    for node in STEP_NODES:
        graph.add_edge(node, "validate_result")
    graph.add_edge("validate_result", END)
    return graph.compile(checkpointer=checkpointer or build_checkpointer())


basic_graph = build_basic_graph()