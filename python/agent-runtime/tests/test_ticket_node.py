import re

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_ticket_node() -> None:
    response = client.post(
        "/internal/agents/run",
        json={
            "agent_type": "ticket",
            "conversation_id": "ticket-create",
            "message": "紧急：设备 E-1024 反复重启，请创建维修工单",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert "已创建工单 TK-" in body["answer"]
    assert "优先级 HIGH" in body["answer"]


def test_query_ticket_node_roundtrip() -> None:
    created = client.post(
        "/internal/agents/run",
        json={"agent_type": "ticket", "conversation_id": "ticket-rt", "message": "创建工单：设备报修咨询"},
    )
    ticket_id = re.search(r"TK-\d+", created.json()["answer"]).group()
    queried = client.post(
        "/internal/agents/run",
        json={"agent_type": "ticket", "conversation_id": "ticket-rt", "message": f"查询工单 {ticket_id} 当前状态"},
    )
    assert queried.status_code == 200
    body = queried.json()
    assert body["status"] == "COMPLETED"
    assert "当前状态 OPEN" in body["answer"]
