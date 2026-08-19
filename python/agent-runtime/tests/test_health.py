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
    assert response.json()["status"] == "ACCEPTED"

