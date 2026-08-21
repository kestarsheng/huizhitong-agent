# Ticket MCP Server

提供售后工单创建与查询工具，默认通过 stdio 运行，供 Agent Runtime 使用 MCP Client 接入。

```powershell
python -m app.server
```

## 存储

默认使用 SQLite（数据文件位于系统临时目录，便于本地演示），可通过 `TICKET_STORAGE=mysql` 切换为 MySQL，库表不存在时自动创建。

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| TICKET_STORAGE | sqlite | sqlite 或 mysql |
| TICKET_MYSQL_HOST | localhost | MySQL 地址 |
| TICKET_MYSQL_PORT | 3306 | MySQL 端口 |
| TICKET_MYSQL_USER | root | MySQL 用户 |
| TICKET_MYSQL_PASSWORD | root | MySQL 密码 |
| TICKET_MYSQL_DATABASE | huizhitong | 数据库名（不存在时自动创建） |

MySQL 建表脚本见 [schema.sql](./schema.sql)。
