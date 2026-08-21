import asyncio

from fastapi.testclient import TestClient

from app.graph.basic_graph import basic_graph
from app.main import app

client = TestClient(app)


def _run(message: str, conversation_id: str):
    return asyncio.run(
        basic_graph.ainvoke(
            {
                "agent_type": "assistant",
                "conversation_id": conversation_id,
                "user_message": message,
            },
            config={"configurable": {"thread_id": conversation_id}},
        )
    )


def test_single_intent_plan_and_validate() -> None:
    result = _run("设备故障怎么处理", "plan-single")
    assert result["plan"] == ["knowledge"]
    assert result["status"] == "WAITING_RAG"
    assert "设备故障排查" in result["answer"]


def test_composite_intent_fans_out_in_parallel() -> None:
    result = _run("查一下 P1002 的库存，顺便问 E-1024 怎么处理", "plan-parallel")
    assert result["plan"] == ["inventory", "knowledge"]
    assert len(result["step_answers"]) == 2
    assert "P1002" in result["answer"]
    assert "E-1024" in result["answer"]


def test_checkpoint_resets_step_outputs_per_turn() -> None:
    first = _run("E-1024 怎么处理", "plan-reset")
    assert "E-1024" in first["answer"]
    second = _run("创建工单：投影仪无法开机", "plan-reset")
    assert second["plan"] == ["ticket"]
    assert len(second["step_answers"]) == 1
    assert "TK-" in second["answer"]
    assert "E-1024" not in second["answer"]


def test_stream_emits_plan_and_validate_nodes() -> None:
    response = client.post(
        "/internal/agents/stream",
        json={
            "agent_type": "knowledge",
            "conversation_id": "plan-stream",
            "message": "E-1024 故障代码怎么处理？",
        },
    )
    assert response.status_code == 200
    assert "plan_task" in response.text
    assert "validate_result" in response.text
    assert "event: done" in response.text