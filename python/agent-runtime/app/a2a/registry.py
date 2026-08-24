"""A2A 智能体注册表：定义可协同的智能体与规则匹配器。

智能体 id 与 LangGraph 节点名解耦：注册表负责"业务智能体"概念，
编排层通过 AGENT_NODE_MAP 将智能体 id 映射为图节点执行。
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDef:
    agent_id: str
    name: str
    description: str
    node: str
    keywords: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()


AGENTS: dict[str, AgentDef] = {
    "customer_service": AgentDef(
        agent_id="customer_service",
        name="客服智能体",
        description="统一入口智能体，识别用户意图并转发给商品知识、库存分析、工单处理等专业智能体协同处理，最终汇总答复。",
        node="general",
        keywords=("你好", "咨询", "请问", "介绍"),
    ),
    "inventory_analysis": AgentDef(
        agent_id="inventory_analysis",
        name="库存分析智能体",
        description="查询商品库存、分析缺货风险并给出补货建议。",
        node="inventory",
        keywords=("库存", "商品", "销量", "补货"),
        patterns=(r"P\d{4}",),
        tools=("query_inventory", "analyze_inventory_risk"),
    ),
    "product_knowledge": AgentDef(
        agent_id="product_knowledge",
        name="商品知识智能体",
        description="基于 RAG 知识库回答设备故障、维修手册、错误码等问题。",
        node="knowledge",
        keywords=("故障", "维修", "手册", "怎么处理", "错误码"),
        patterns=(r"E-\d{3,}",),
    ),
    "ticket_handling": AgentDef(
        agent_id="ticket_handling",
        name="工单处理智能体",
        description="查询工单状态、创建售后与报修工单。",
        node="ticket",
        keywords=("工单", "售后", "投诉", "报修", "维修申请"),
        patterns=(r"TK-\d{3,}",),
        tools=("create_ticket", "query_ticket"),
    ),
}


AGENT_NODE_MAP: dict[str, str] = {agent_id: agent.node for agent_id, agent in AGENTS.items()}


def match_agents(message: str) -> list[str]:
    """规则匹配：返回命中的工作智能体 id；未命中时回落到客服智能体。"""
    hits: list[str] = []
    for agent_id, agent in AGENTS.items():
        if agent_id == "customer_service":
            continue
        keyword_hit = any(word in message for word in agent.keywords)
        pattern_hit = any(re.search(pattern, message, re.IGNORECASE) for pattern in agent.patterns)
        if keyword_hit or pattern_hit:
            hits.append(agent_id)
    return hits or ["customer_service"]