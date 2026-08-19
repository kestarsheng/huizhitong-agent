from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/internal/health")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_run_agent_contract() -> None:
    response = client.post(
        "/internal/agents/run",
        json={
            "agent_type": "knowledge",
            "conversation_id": "conv-1",
            "message": "你好",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


def test_knowledge_route() -> None:
    response = client.post(
        "/internal/agents/run",
        json={
            "agent_type": "knowledge",
            "conversation_id": "conv-2",
            "message": "设备故障怎么处理",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "WAITING_RAG"


def test_same_conversation_can_use_thread_id() -> None:
    payload = {
        "agent_type": "knowledge",
        "conversation_id": "thread-1",
        "message": "设备维修手册在哪里",
    }
    first = client.post("/internal/agents/run", json=payload)
    second = client.post("/internal/agents/run", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["conversation_id"] == second.json()["conversation_id"]


def test_inventory_tool_node() -> None:
    response = client.post(
        "/internal/agents/run",
        json={
            "agent_type": "inventory",
            "conversation_id": "thread-inventory",
            "message": "分析商品 P1002 库存",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"
    assert "建议补货" in response.json()["answer"]


def test_deepseek_disabled_fallback(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_ENABLED", "false")
    response = client.post(
        "/internal/agents/run",
        json={"agent_type": "general", "conversation_id": "general-1", "message": "你好"},
    )
    assert response.status_code == 200
    assert "未启用 DeepSeek" in response.json()["answer"]

