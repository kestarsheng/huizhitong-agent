import sys

from fastapi.testclient import TestClient

from app.audit.recorder import AuditRecorder
from app.main import app


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql: str, params=None) -> None:
        self.executed.append((sql, params))

    def fetchall(self):
        return []


class FakeConn:
    def __init__(self) -> None:
        self.cursor_obj = FakeCursor()
        self.description = []

    def cursor(self):
        return self.cursor_obj

    def close(self) -> None:
        pass


class FakeChannel:
    def __init__(self) -> None:
        self.published: list[dict] = []

    def exchange_declare(self, **kwargs) -> None:
        pass

    def basic_publish(self, **kwargs) -> None:
        self.published.append(kwargs)


class FakePika:
    class URLParameters:
        def __init__(self, url: str) -> None:
            self.url = url

    class BlockingConnection:
        def __init__(self, params) -> None:
            self.ch = FakeChannel()

        def channel(self):
            return self.ch

        def close(self) -> None:
            pass

    class BasicProperties:
        def __init__(self, **kwargs) -> None:
            self.__dict__.update(kwargs)


def test_record_writes_db_when_mq_disabled(monkeypatch):
    recorder = AuditRecorder(mysql={"host": "x", "port": 3306, "user": "u", "password": "p", "database": "d"}, mq_url="")
    conn = FakeConn()
    monkeypatch.setattr(recorder, "_connect", lambda: conn)
    transport = recorder.record(
        conversation_id="c1", agent_type="knowledge", tenant_id="1",
        message="E-1024 怎么处理", status="WAITING_RAG", node_count=4, latency_ms=12,
    )
    assert transport == "db"
    assert any("CREATE TABLE IF NOT EXISTS audit_call" in sql for sql, _ in conn.cursor_obj.executed)
    assert any("INSERT INTO audit_call" in sql for sql, _ in conn.cursor_obj.executed)


def test_record_publishes_to_mq(monkeypatch):
    monkeypatch.setitem(sys.modules, "pika", FakePika())
    recorder = AuditRecorder(mysql={}, mq_url="amqp://localhost:5672")
    transport = recorder.record(
        conversation_id="c2", agent_type="ticket", tenant_id="",
        message="创建工单", status="COMPLETED", node_count=4, latency_ms=30,
    )
    assert transport == "mq"


def test_record_falls_back_when_mq_unreachable(monkeypatch):
    class BrokenPika:
        class URLParameters:
            def __init__(self, url: str) -> None:
                self.url = url

        class BlockingConnection:
            def __init__(self, params) -> None:
                raise RuntimeError("connection refused")

    monkeypatch.setitem(sys.modules, "pika", BrokenPika())
    recorder = AuditRecorder(mysql={}, mq_url="amqp://localhost:5672")
    conn = FakeConn()
    monkeypatch.setattr(recorder, "_connect", lambda: conn)
    transport = recorder.record(
        conversation_id="c3", agent_type="general", tenant_id="",
        message="你好", status="COMPLETED", node_count=4, latency_ms=9,
    )
    assert transport == "db"


def test_audit_list_api(monkeypatch):
    class FakeRecorder:
        def list(self, limit, agent_type, status):
            return [{
                "id": 1,
                "conversation_id": "c1",
                "agent_type": "knowledge",
                "tenant_id": "1",
                "message": "E-1024",
                "status": "WAITING_RAG",
                "node_count": 4,
                "latency_ms": 12,
                "model": "deepseek",
                "created_at": "2026-08-21T10:00:00",
            }]

    import app.api.routes as routes
    monkeypatch.setattr(routes, "audit_recorder", FakeRecorder())
    response = TestClient(app).get("/internal/audit/calls")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["conversation_id"] == "c1"