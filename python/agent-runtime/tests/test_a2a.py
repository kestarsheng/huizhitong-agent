"""A2A 跨智能体协同测试：注册表匹配、LLM 路由降级、协同汇总与智能体链路。"""
import asyncio
import json

from app.a2a import router
from app.a2a.registry import match_agents
from app.graph import basic_graph as graph_module
from app.graph.basic_graph import basic_graph
from app.llm import gateway


def test_match_agents_inventory() -> None:
    assert match_agents("查一下商品 P1001 的库存") == ["inventory_analysis"]


def test_match_agents_knowledge() -> None:
    assert match_agents("E-1024 故障代码怎么处理") == ["product_knowledge"]


def test_match_agents_ticket() -> None:
    assert match_agents("请帮我创建报修工单") == ["ticket_handling"]


def test_match_agents_general_fallback() -> None:
    assert match_agents("你好，介绍一下你自己") == ["customer_service"]


def test_match_agents_multi() -> None:
    result = match_agents("查一下 P1002 库存，顺便问 E-1024 怎么处理")
    assert "inventory_analysis" in result
    assert "product_knowledge" in result


def test_llm_routing_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("A2A_LLM_ROUTING", raising=False)
    assert asyncio.run(router.llm_route("任意消息")) is None


def test_llm_route_parses_json(monkeypatch) -> None:
    monkeypatch.setenv("A2A_LLM_ROUTING", "true")

    async def fake_answer(system_prompt, user_message, provider=None):
        return json.dumps(["inventory_analysis", "product_knowledge"], ensure_ascii=False)

    monkeypatch.setattr(gateway, "generate_answer", fake_answer)
    assert asyncio.run(router.llm_route("查库存并看手册")) == ["inventory_analysis", "product_knowledge"]


def test_llm_route_ignores_unknown_ids(monkeypatch) -> None:
    monkeypatch.setenv("A2A_LLM_ROUTING", "true")

    async def fake_answer(system_prompt, user_message, provider=None):
        return '["inventory_analysis", "not_exist"]'

    monkeypatch.setattr(gateway, "generate_answer", fake_answer)
    assert asyncio.run(router.llm_route("查库存")) == ["inventory_analysis"]


def test_llm_route_returns_none_on_bad_output(monkeypatch) -> None:
    monkeypatch.setenv("A2A_LLM_ROUTING", "true")

    async def fake_answer(system_prompt, user_message, provider=None):
        return "抱歉，无法解析。"

    monkeypatch.setattr(gateway, "generate_answer", fake_answer)
    assert asyncio.run(router.llm_route("查库存")) is None


def _disable_llm(monkeypatch) -> None:
    monkeypatch.delenv("A2A_LLM_ROUTING", raising=False)
    monkeypatch.setenv("DEEPSEEK_ENABLED", "false")
    monkeypatch.delenv("QWEN_API_KEY", raising=False)

    async def no_llm(*args, **kwargs):
        return None

    monkeypatch.setattr(graph_module, "generate_answer", no_llm)


def test_multi_agent_synthesis_falls_back(monkeypatch) -> None:
    _disable_llm(monkeypatch)
    state = asyncio.run(basic_graph.ainvoke(
        {
            "agent_type": "assistant",
            "conversation_id": "a2a-synth-1",
            "user_message": "查一下 P1002 库存，顺便问 E-1024 怎么处理",
        },
        config={"configurable": {"thread_id": "a2a-synth-1"}},
    ))
    assert state["status"] == "WAITING_RAG"
    assert "建议补货" in state["answer"]
    assert "知识库检索结果" in state["answer"]


def test_ticket_priority_over_knowledge(monkeypatch) -> None:
    _disable_llm(monkeypatch)
    state = asyncio.run(basic_graph.ainvoke(
        {
            "agent_type": "ticket",
            "conversation_id": "a2a-ticket-prio",
            "user_message": "打印机 E-1024 出现故障，请帮我创建维修工单",
        },
        config={"configurable": {"thread_id": "a2a-ticket-prio"}},
    ))
    assert state["plan"] == ["ticket"]
    assert state["status"] == "COMPLETED"
    assert "已创建工单" in state["answer"]

def test_agent_chain_recorded(monkeypatch) -> None:
    _disable_llm(monkeypatch)
    state = asyncio.run(basic_graph.ainvoke(
        {
            "agent_type": "assistant",
            "conversation_id": "a2a-chain-1",
            "user_message": "查一下 P1002 库存，顺便问 E-1024 怎么处理",
        },
        config={"configurable": {"thread_id": "a2a-chain-1"}},
    ))
    assert "customer_service" in state["agent_chain"]
    assert "inventory" in state["agent_chain"]
    assert "knowledge" in state["agent_chain"]
