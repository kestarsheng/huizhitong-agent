from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState
from app.tools.inventory_gateway import inventory_gateway
from app.tools.inventory_gateway import mcp_inventory_gateway
from app.tools.ticket_gateway import mcp_ticket_gateway, ticket_gateway
import os
from app.llm.deepseek import generate_answer
from app.rag.knowledge import knowledge_service
from app.tools.registry_client import tool_registry_client
import re


def classify_intent(state: AgentState) -> AgentState:
    message = state["user_message"]
    if any(word in message for word in ("库存", "商品", "销量")):
        intent = "inventory"
    elif any(word in message for word in ("工单", "售后", "投诉", "报修")):
        intent = "ticket"
    elif any(word in message for word in ("故障", "维修", "手册", "怎么处理")):
        intent = "knowledge"
    else:
        intent = "general"
    return {"intent": intent, "status": "CLASSIFIED"}


def route_by_intent(state: AgentState) -> str:
    return state.get("intent", "general")


async def inventory_node(state: AgentState) -> AgentState:
    if state.get("tenant_id") is not None:
        allowed = await tool_registry_client.available_tools(state.get("agent_type", "inventory"), state["tenant_id"])
        allowed_names = {item.get("toolName") for item in allowed}
        if allowed and not ({"query_inventory", "analyze_inventory_risk"} & allowed_names):
            return {"answer": "当前租户未授权库存工具，请联系管理员开通。", "status": "FORBIDDEN"}
    product_id = re.search(r"P\d{4}", state["user_message"], re.IGNORECASE)
    if product_id is None:
        return {"answer": "请提供商品编号，例如 P1001。", "status": "NEED_INPUT"}
    if os.getenv("MCP_INVENTORY_ENABLED", "false").lower() == "true":
        result = await mcp_inventory_gateway.analyze(product_id.group().upper())
    else:
        result = inventory_gateway.analyze(product_id.group().upper())
    if not result["found"]:
        return {"answer": result["message"], "status": "COMPLETED"}
    answer = (f"商品 {result['product_id']}（{result['product_name']}）当前库存 "
              f"{result['stock']}，安全库存 {result['safe_stock']}，风险等级 {result['risk']}；"
              f"{result['suggestion']}。")
    return {"answer": answer, "status": "COMPLETED"}


async def knowledge_node(state: AgentState) -> AgentState:
    context = knowledge_service.search_context(state["user_message"])
    if not context:
        return {"answer": "知识库暂未检索到相关内容，请补充设备型号、错误码或具体故障现象。", "status": "WAITING_RAG"}
    return {"answer": f"根据知识库检索结果：\n{context}", "status": "WAITING_RAG"}


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
            return {"answer": "当前租户未授权工单工具，请联系管理员开通。", "status": "FORBIDDEN"}
    message = state["user_message"]
    ticket_id_match = re.search(r"TK-\d{3,}", message, re.IGNORECASE)
    if ticket_id_match:
        ticket_id = ticket_id_match.group().upper()
        if os.getenv("MCP_TICKET_ENABLED", "false").lower() == "true":
            result = await mcp_ticket_gateway.query(ticket_id)
        else:
            result = ticket_gateway.query(ticket_id)
        if not result["found"]:
            return {"answer": result["message"], "status": "COMPLETED"}
        return {"answer": (f"工单 {result['ticket_id']}（{result['subject']}）当前状态 {result['status']}，"
                           f"优先级 {result['priority']}。"), "status": "COMPLETED"}
    subject = message[:30].strip()
    if os.getenv("MCP_TICKET_ENABLED", "false").lower() == "true":
        result = await mcp_ticket_gateway.create(subject, message, priority=_parse_ticket_priority(message))
    else:
        result = ticket_gateway.create(subject, message, priority=_parse_ticket_priority(message))
    if not result["created"]:
        return {"answer": result["message"], "status": "COMPLETED"}
    return {"answer": (f"已创建工单 {result['ticket_id']}（{result['subject']}），优先级 {result['priority']}，"
                       f"当前状态 {result['status']}。"), "status": "COMPLETED"}


async def general_node(state: AgentState) -> AgentState:
    answer = await generate_answer(
        "你是汇智通企业智能体助手。请简洁、准确地回答用户问题；无法确认时明确说明。",
        state["user_message"],
    )
    if answer is None:
        answer = "已接收你的问题，当前未启用 DeepSeek 模型或暂未绑定对应业务能力。"
    return {"answer": answer, "status": "COMPLETED"}


def build_basic_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("inventory", inventory_node)
    graph.add_node("knowledge", knowledge_node)
    graph.add_node("ticket", ticket_node)
    graph.add_node("general", general_node)
    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {"inventory": "inventory", "knowledge": "knowledge", "ticket": "ticket", "general": "general"},
    )
    graph.add_edge("inventory", END)
    graph.add_edge("knowledge", END)
    graph.add_edge("ticket", END)
    graph.add_edge("general", END)
    return graph.compile(checkpointer=checkpointer)


basic_graph = build_basic_graph(MemorySaver())

