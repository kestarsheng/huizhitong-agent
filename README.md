# 汇智通智能体协同中台

企业级智能体协同中台，采用 Java 微服务承载业务与治理能力，Python 承载 LangGraph Agent、RAG 与 MCP 能力，Vue 3 提供管理控制台和对话入口。

## 目录

- `frontend/`：Vue 3 管理端与对话端
- `java/`：Spring Boot / Spring Cloud Alibaba 微服务
- `python/`：FastAPI Agent Runtime
- `mcp-servers/`：MCP 工具服务
- `deploy/`：本地基础设施与容器编排
- `docs/`：架构、接口和数据设计文档

## 当前阶段

项目处于基础骨架阶段，后续按功能分支逐步实现：

1. Java 公共模块与网关
2. Python Agent Runtime
3. 智能体管理与调用链路
4. LangGraph 编排与 SSE 流式输出
5. MCP 工具接入
6. RAG 知识库
7. 前端控制台与部署

## 本地服务端口

| 服务 | 端口 | 入口 |
| --- | ---: | --- |
| Vue 管理控制台 | 5173 | `http://localhost:5173` |
| Java Tool Service | 8083 | `http://localhost:8083/internal/tools` |
| Python Agent Runtime | 8000 | `http://localhost:8000/internal/health` |
| Milvus | 19530 | `http://localhost:19530` |

## 本地启动

1. 启动基础设施：`docker compose -f deploy/docker-compose.infra.yml up -d`
2. 启动 Java Tool Service：在 `java/` 执行 `mvn -pl huizhitong-tool-service spring-boot:run`
3. 启动 Python Runtime：在 `python/agent-runtime` 执行 `hzt-agent-venv\\Scripts\\python.exe -m uvicorn app.main:app --reload --port 8000`
4. 启动前端：在 `frontend/` 执行 `npm run dev`

## 开发约定

- 主分支：`main`
- 集成分支：`develop`
- 功能分支：`feature/<module>-<feature>`
- Commit：`英文类型(英文模块): 中文说明`
