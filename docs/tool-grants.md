# 工具授权管理（RBAC 多租户资源管控）

## 设计

- **工具注册中心**（Java Tool Service，8083）：`tool_registry` 表保存平台工具定义，
  启动时幂等注册内置工具（库存查询/风险分析/建单/查单）；
- **授权关系**：`tool_grants` 表按 `(agent_type, tenant_id, tool_id)` 记录租户
  对智能体可用的工具授权，多租户隔离；
- **鉴权链路**：Python Agent Runtime 在工具节点执行前调用
  `GET /internal/tools/available?agentType=&tenantId=` 拉取已授权工具；
  授权缺失时返回 `FORBIDDEN`，不调用任何 MCP 工具；
- **管理端**：前端「授权管理」页按智能体类型 + 租户查看/新增/撤销授权。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/internal/tools/grants?agentType=&tenantId=` | 查询授权记录（可按智能体/租户过滤） |
| `POST` | `/internal/tools/grants` | 新增授权（幂等） |
| `DELETE` | `/internal/tools/grants?agentType=&tenantId=&toolId=` | 撤销授权 |
| `GET` | `/internal/tools/available?agentType=&tenantId=` | 返回该租户可用（已授权且启用）的工具 |

## 端到端验证

租户只授权 `create_ticket` 时调用库存分析智能体：

```
STATUS=FORBIDDEN
ANSWER=当前租户未授权库存工具，请联系管理员开通。
```

补授权 `query_inventory` 后同一请求：

```
STATUS=COMPLETED
ANSWER=商品 P1002（工业温度传感器）当前库存 18，安全库存 30，风险等级 HIGH；建议补货。
```