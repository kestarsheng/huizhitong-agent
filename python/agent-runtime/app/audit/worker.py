"""RabbitMQ 审计消费者：订阅 audit.call 路由，异步写入 MySQL。

运行：python -m app.audit.worker
前置：pip install pika，且配置 AUDIT_MQ_URL。
连接中断时自动重连，重试间隔由 AUDIT_WORKER_RECONNECT_DELAY 控制（默认 5 秒）。
"""
import json
import logging
import os
import time

import pymysql

logger = logging.getLogger(__name__)

_RECONNECT_DELAY = float(os.getenv("AUDIT_WORKER_RECONNECT_DELAY", "5"))

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


def _mysql_config() -> dict:
    return {
        "host": os.getenv("AUDIT_MYSQL_HOST", os.getenv("TICKET_MYSQL_HOST", "localhost")),
        "port": int(os.getenv("AUDIT_MYSQL_PORT", os.getenv("TICKET_MYSQL_PORT", "3306"))),
        "user": os.getenv("AUDIT_MYSQL_USER", os.getenv("TICKET_MYSQL_USER", "root")),
        "password": os.getenv("AUDIT_MYSQL_PASSWORD", os.getenv("TICKET_MYSQL_PASSWORD", "root")),
        "database": os.getenv("AUDIT_MYSQL_DATABASE", os.getenv("TICKET_MYSQL_DATABASE", "huizhitong")),
    }


def _ensure_table(config: dict) -> None:
    """启动时确保 audit_call 表存在（全新 MySQL 首次部署自建表）。"""
    conn = pymysql.connect(**config, charset="utf8mb4", autocommit=True)
    try:
        with conn.cursor() as cursor:
            cursor.execute(_AUDIT_TABLE_SQL)
    finally:
        conn.close()


def _insert(config: dict, payload: dict) -> None:
    conn = pymysql.connect(**config, charset="utf8mb4", autocommit=True)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                _INSERT_SQL,
                (
                    payload["conversation_id"],
                    payload["agent_type"],
                    payload.get("tenant_id", ""),
                    payload["message"],
                    payload["status"],
                    payload.get("node_count", 0),
                    payload.get("latency_ms", 0),
                    payload.get("model", ""),
                ),
            )
    finally:
        conn.close()


def _consume(config: dict, mq_url: str) -> None:
    """连接 RabbitMQ 并阻塞消费；连接被断开时抛异常，由 main 循环重连。"""
    import pika

    connection = pika.BlockingConnection(pika.URLParameters(mq_url))
    try:
        channel = connection.channel()
        channel.exchange_declare(exchange="huizhitong.audit", exchange_type="topic", durable=True)
        channel.queue_declare(queue="audit.call.queue", durable=True)
        channel.queue_bind(queue="audit.call.queue", exchange="huizhitong.audit", routing_key="audit.call")
        channel.basic_qos(prefetch_count=10)

        def callback(ch, method, properties, body) -> None:
            try:
                payload = json.loads(body.decode("utf-8"))
                _insert(config, payload)
                ch.basic_ack(method.delivery_tag)
            except Exception as exc:
                logger.error("审计消息处理失败: %s", exc)
                ch.basic_nack(method.delivery_tag, requeue=True)

        channel.basic_consume(queue="audit.call.queue", on_message_callback=callback)
        print("audit worker started, waiting for messages...")
        channel.start_consuming()
    finally:
        try:
            connection.close()
        except Exception:
            pass


def main() -> None:
    import pika  # noqa: F401 提前暴露依赖缺失

    mq_url = os.getenv("AUDIT_MQ_URL", "")
    if not mq_url:
        raise SystemExit("AUDIT_MQ_URL 未配置")
    config = _mysql_config()
    _ensure_table(config)
    while True:
        try:
            _consume(config, mq_url)
        except KeyboardInterrupt:
            logger.info("audit worker 手动停止")
            return
        except Exception as exc:
            logger.error("审计消费连接中断，%.0f 秒后重连: %s", _RECONNECT_DELAY, exc)
            time.sleep(_RECONNECT_DELAY)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()