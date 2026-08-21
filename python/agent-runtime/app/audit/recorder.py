"""调用审计记录器。

- 配置 AUDIT_MQ_URL 且已安装 pika 时，调用记录先发布到 RabbitMQ（topic 交换机
  huizhitong.audit / 路由键 audit.call），由独立 worker 异步入库；
- 未配置 MQ、发布失败或直写失败时逐级降级，保证主链路不受审计 IO 影响。
"""
import json
import logging
import os

import pymysql

logger = logging.getLogger(__name__)

_AUDIT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_call (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(100) NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    tenant_id VARCHAR(64) NOT NULL DEFAULT '',
    message VARCHAR(500) NOT NULL,
    status VARCHAR(32) NOT NULL,
    node_count INT NOT NULL DEFAULT 0,
    latency_ms INT NOT NULL DEFAULT 0,
    model VARCHAR(64) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_created_at (created_at),
    KEY idx_agent_type (agent_type)
) DEFAULT CHARSET=utf8mb4
"""

_INSERT_SQL = (
    "INSERT INTO audit_call "
    "(conversation_id, agent_type, tenant_id, message, status, node_count, latency_ms, model) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
)


class AuditRecorder:
    """调用审计记录器：RabbitMQ 异步优先，失败自动降级直写 MySQL。"""

    def __init__(self, mysql: dict | None = None, mq_url: str | None = None):
        self._mysql = mysql or {
            "host": os.getenv("AUDIT_MYSQL_HOST", os.getenv("TICKET_MYSQL_HOST", "localhost")),
            "port": int(os.getenv("AUDIT_MYSQL_PORT", os.getenv("TICKET_MYSQL_PORT", "3306"))),
            "user": os.getenv("AUDIT_MYSQL_USER", os.getenv("TICKET_MYSQL_USER", "root")),
            "password": os.getenv("AUDIT_MYSQL_PASSWORD", os.getenv("TICKET_MYSQL_PASSWORD", "root")),
            "database": os.getenv("AUDIT_MYSQL_DATABASE", os.getenv("TICKET_MYSQL_DATABASE", "huizhitong")),
        }
        self._mq_url = mq_url if mq_url is not None else os.getenv("AUDIT_MQ_URL", "")
        self._table_ready = False

    def _connect(self):
        return pymysql.connect(**self._mysql, charset="utf8mb4", autocommit=True)

    def _ensure_table(self) -> None:
        if self._table_ready:
            return
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(_AUDIT_TABLE_SQL)
            self._table_ready = True
        finally:
            conn.close()

    def record(
        self,
        *,
        conversation_id: str,
        agent_type: str,
        tenant_id: str = "",
        message: str,
        status: str,
        node_count: int = 0,
        latency_ms: int = 0,
        model: str = "deepseek",
    ) -> str:
        """记录一次智能体调用，返回实际落库通道：mq / db / none。"""
        payload = {
            "conversation_id": conversation_id[:100],
            "agent_type": agent_type[:100],
            "tenant_id": str(tenant_id or "")[:64],
            "message": message[:500],
            "status": status[:32],
            "node_count": int(node_count),
            "latency_ms": int(latency_ms),
            "model": model[:64],
        }
        if self._mq_url:
            try:
                self._publish(payload)
                return "mq"
            except Exception as exc:
                logger.warning("RabbitMQ 发布失败，降级直写 MySQL: %s", exc)
        try:
            self._ensure_table()
            self._insert(payload)
            return "db"
        except Exception as exc:
            logger.warning("审计直写 MySQL 失败: %s", exc)
            return "none"

    def _publish(self, payload: dict) -> None:
        import pika

        connection = pika.BlockingConnection(pika.URLParameters(self._mq_url))
        try:
            channel = connection.channel()
            channel.exchange_declare(exchange="huizhitong.audit", exchange_type="topic", durable=True)
            channel.basic_publish(
                exchange="huizhitong.audit",
                routing_key="audit.call",
                body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                properties=pika.BasicProperties(delivery_mode=2),
            )
        finally:
            connection.close()

    def _insert(self, payload: dict) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    _INSERT_SQL,
                    (
                        payload["conversation_id"],
                        payload["agent_type"],
                        payload["tenant_id"],
                        payload["message"],
                        payload["status"],
                        payload["node_count"],
                        payload["latency_ms"],
                        payload["model"],
                    ),
                )
        finally:
            conn.close()

    def list(self, *, limit: int = 50, agent_type: str | None = None, status: str | None = None) -> list[dict]:
        self._ensure_table()
        conn = self._connect()
        try:
            with conn.cursor() as cursor:
                sql = (
                    "SELECT id, conversation_id, agent_type, tenant_id, message, status, "
                    "node_count, latency_ms, model, created_at FROM audit_call"
                )
                conditions: list[str] = []
                params: list[object] = []
                if agent_type:
                    conditions.append("agent_type = %s")
                    params.append(agent_type)
                if status:
                    conditions.append("status = %s")
                    params.append(status)
                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)
                sql += " ORDER BY id DESC LIMIT %s"
                params.append(int(limit))
                cursor.execute(sql, tuple(params))
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            conn.close()


audit_recorder = AuditRecorder()