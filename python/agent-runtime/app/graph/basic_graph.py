from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import AgentState


def classify_intent(state: AgentState) -> AgentState:
    message = state["user_message"]
    if any(word in message for word in ("库存", "商品", "销量")):
        intent = "inventory"
    elif any(word in message for word in ("故障", "维修", "手册", "怎么处理")):
        intent = "knowledge"
    elif any(word in message for word in ("工单", "售后", "投诉")):
        intent = "ticket"
    else:
        intent = "general"
    return {"intent": intent, "status": "CLASSIFIED"}


def route_by_intent(state: AgentState) -> str:
    return state.get("intent", "general")


def inventory_node(state: AgentState) -> AgentState:
    return {"answer": "已识别为库存分析任务，等待接入库存 MCP 工具。", "status": "WAITING_TOOL"}


def knowledge_node(state: AgentState) -> AgentState:
    return {"answer": "已识别为知识问答任务，等待接入 RAG 检索链路。", "status": "WAITING_RAG"}


def ticket_node(state: AgentState) -> AgentState:
    return {"answer": "已识别为工单处理任务，等待接入工单 MCP 工具。", "status": "WAITING_TOOL"}


def general_node(state: AgentState) -> AgentState:
    return {"answer": "已接收你的问题，当前基础编排图暂未绑定对应业务能力。", "status": "COMPLETED"}


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

