"""RabbitMQ 审计消费者：订阅 audit.call 路由，异步写入 MySQL。

运行：python -m app.audit.worker
前置：pip install pika，且配置 AUDIT_MQ_URL。
"""
import json
import logging
import os

import pymysql

logger = logging.getLogger(__name__)

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


def main() -> None:
    import pika

    mq_url = os.getenv("AUDIT_MQ_URL", "")
    if not mq_url:
        raise SystemExit("AUDIT_MQ_URL 未配置")
    config = _mysql_config()
    connection = pika.BlockingConnection(pika.URLParameters(mq_url))
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()