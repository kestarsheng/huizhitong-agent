# Agent 编排：LangGraph 状态机

## 图结构

```mermaid
flowchart LR
    START --> classify[意图识别 classify_intent]
    classify --> plan[任务规划 plan_task]
    plan -->|单意图| inv[库存查询 inventory]
    plan -->|单意图| tk[工单处理 ticket]
    plan -->|单意图| kb[知识检索 knowledge]
    plan -->|单意图| gen[通用回答 general]
    plan -->|多意图 Send 并行| inv
    plan -->|多意图 Send 并行| kb
    inv --> validate[结果校验 validate_result]
    tk --> validate
    kb --> validate
    gen --> validate
    validate --> END
```

## 节点职责

| 节点 | 职责 |
| --- | --- |
| `classify_intent` | 识别库存/工单/知识/通用意图；命中多类时产出 `intents` 列表并重置本回合步骤输出 |
| `plan_task` | 将意图列表转为可执行节点序列 `plan` |
| `inventory` / `ticket` / `knowledge` / `general` | 执行具体步骤：MCP/本地工具调用、RAG 检索、模型生成，统一写 `step_answers` 与 `step_statuses` |
| `validate_result` | 聚合并行分支答案，按 FORBIDDEN > NEED_INPUT > WAITING_RAG > COMPLETED 选取最终状态 |

## 条件路由与并行

- 单意图：`plan_task` 条件边直接进入对应节点；
- 多意图（如“查库存 + 查故障处理”）：通过 `Send` 并行展开多个分支，
  分支通过 `resetable_add` 累加器合并到 `step_answers`，结果校验节点幂等聚合；
- 多轮会话：`classify_intent` 每回合写入重置标记，清空上一回合步骤输出，
  Checkpoint 仅保留会话级状态。

## Checkpoint 持久化

| 环境变量 | 默认 | 说明 |
| --- | --- | --- |
| `AGENT_CHECKPOINT` | `memory` | `memory` 仅内存；`postgres` 强制 PG；`auto` 可用时自动启用 |
| `PG_DSN` | 空 | 例如 `postgresql://postgres:postgres@localhost:5432/huizhitong_agent` |

PG 依赖通过 `pip install -e ".[checkpoint-postgres]"` 安装；
未配置或连接失败时自动降级 `MemorySaver`，链路不受影响。

## 测试

`tests/test_graph_planning.py` 覆盖单意图规划、多意图并行展开、
跨回合状态重置与 SSE 节点事件完整性。