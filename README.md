# 汇智通智能体协同中台

面向企业运营、客服与销售部门的智能体协同中台：Java 微服务承载业务与治理能力，Python 承载 LangGraph 智能体编排、RAG 与 MCP 工具接入，Vue 3 提供管理控制台与对话入口。

## 目录

- `frontend/`：Vue 3 管理端与对话端（Vite + Element Plus）
- `java/`：Spring Boot / Spring Cloud Alibaba 微服务（网关、工具服务等）
- `python/`：FastAPI Agent Runtime（LangGraph 编排、RAG、MCP 客户端）
- `mcp-servers/`：MCP 工具服务
- `deploy/`：Docker Compose 基础设施（RabbitMQ、Milvus/etcd/MinIO）
- `scripts/`：本地一键启停脚本
- `docs/`：架构、接口与设计文档

## 已实现能力

- LangGraph 多智能体编排：意图分类 → 任务规划 → 并行扇出 → 结果校验，SSE 流式输出
- RAG 混合检索：BGE-M3 稠密 + 稀疏 → RRF 融合 → BGE-reranker-large 重排，Milvus / 内存向量库自动切换
- MCP 工具接入：库存查询、工单查询等工具经 MCP 协议统一封装，支持注册与目录刷新
- 双模型网关：DeepSeek 主模型 + 通义千问降级路由，主模型异常自动切换（LLM_PROVIDER / LLM_FALLBACK 可配）
- A2A 跨智能体协同：客服智能体入口识别意图，经 LLM/规则路由并行转发库存、知识、工单专业智能体，协同汇总统一答复
- 工具授权（RBAC）：按智能体类型与租户授权/撤销工具，未授权工具在对话中返回 FORBIDDEN，多租户资源隔离
- JWT 登录与网关鉴权：Spring Security + JWT 签发/校验，Gateway 统一鉴权并透传用户头，工具服务二次校验
- 调用审计：RabbitMQ 异步落库 MySQL，MQ 故障自动降级直写，独立 worker 消费并自动重连
- Java 微服务骨架：Spring Cloud Gateway + Nacos 注册发现、工具服务 REST 接口

## 本地服务端口

| 服务 | 端口 | 入口 |
| --- | ---: | --- |
| Vue 管理控制台 | 5173 | http://localhost:5173 |
| Java Tool Service | 8083 | http://localhost:8083/internal/tools |
| Python Agent Runtime | 8000 | http://localhost:8000/internal/health |
| Spring Cloud Gateway | 8080 | http://localhost:8080/actuator/health |
| RabbitMQ 管理台 | 15672 | http://localhost:15672 |
| Milvus | 19530 | http://localhost:19530 |

## 快速启动

### 1. 基础设施

```powershell
docker compose -f deploy/docker-compose.infra.yml up -d
```

### 2. 本地敏感配置

复制 `scripts/env.local.ps1.example` 为 `scripts/env.local.ps1`，填写 API Key 与 MySQL 密码（该文件已 gitignore，不会入库）。

### 3. 一键启动 Python 服务

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-services.ps1
```

脚本依次完成：启动 RabbitMQ → 启动 Agent Runtime（8000）→ 启动审计 worker，日志输出到 `logs/`。停止：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/stop-services.ps1
```

### 4. Java / 前端

```powershell
cd java
mvn -pl huizhitong-tool-service spring-boot:run
```

```powershell
cd frontend
npm run dev
```

## 开发约定

- 主分支：`main`；集成分支：`develop`
- 功能分支：`feature/<module>-<feature>`
- Commit：`英文类型(英文模块): 中文说明`