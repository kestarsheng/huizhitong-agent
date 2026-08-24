# 调用审计：RabbitMQ 异步解耦 + MySQL 持久化

## 链路

```mermaid
flowchart LR
    Web[前端] --> API[Agent Runtime /internal/agents/*]
    API -->|调用结束| R[AuditRecorder]
    R -->|AUDIT_MQ_URL 已配置| MQ[(RabbitMQ audit.call)]
    R -->|MQ 不可用/未配置| DB[(MySQL audit_call)]
    MQ --> W[audit worker]
    W --> DB
    Web -->|GET /internal/audit/calls| DB
```

## 设计

- 每次智能体调用（run / stream）结束后记录：会话、智能体类型、租户、问题摘要、
  状态、节点数、耗时、模型；
- 审计写入通过 `asyncio.to_thread` 异步执行，且失败只告警，绝不影响主回答链路；
- 传输通道三级降级：RabbitMQ 发布 → 直写 MySQL → 丢弃并告警；
- 独立消费者 `python -m app.audit.worker` 订阅 `audit.call`，消息确认 + 失败重入队；
- worker 连接中断自动重连（间隔 `AUDIT_WORKER_RECONNECT_DELAY` 秒，默认 5），
  RabbitMQ 重启后无需人工干预。

## 启用异步通道

1. 启动 RabbitMQ：`docker compose -f deploy/docker-compose.infra.yml up -d rabbitmq`
2. 安装依赖：`pip install -e ".[audit-mq]"`（pika）
3. 配置环境变量：`AUDIT_MQ_URL=amqp://huizhitong:huizhitong@localhost:5672`
4. 启动消费者：`python -m app.audit.worker`

也可以直接运行 `scripts/start-services.ps1`，脚本会依次拉起 RabbitMQ、Agent Runtime
与审计 worker；`scripts/stop-services.ps1` 负责停止。

未配置 `AUDIT_MQ_URL` 时，记录自动直写 MySQL（复用 `TICKET_MYSQL_*` 配置），
前端「调用审计」页面立即可用。

## 测试

`tests/test_audit.py` 覆盖：MQ 未配置直写 DB、MQ 发布成功、
MQ 不可用降级 DB、审计查询 API。