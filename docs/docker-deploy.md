# Docker 一键部署

把汇智通整套系统容器化：MySQL、RabbitMQ、工具服务、网关、Agent Runtime、审计 Worker、前端共 7 个容器，
一条命令拉起，适合演示与交付。

## 架构

| 服务 | 容器名 | 宿主机端口 | 说明 |
| --- | --- | --- | --- |
| 前端（nginx） | huizhitong-frontend | 5173 | 静态资源 + `/api` 反代到网关 |
| Gateway | huizhitong-gateway | 8080 | 统一鉴权与路由 |
| Tool Service | huizhitong-tool-service | 8083 | 登录 / 工具注册 / 授权 / 用户管理 |
| Agent Runtime | huizhitong-agent-runtime | 8000 | LangGraph 编排 + RAG + SSE |
| Audit Worker | huizhitong-audit-worker | — | RabbitMQ 消费审计消息入库 |
| RabbitMQ | huizhitong-rabbitmq | 5673 / 15673 | 异步审计（15673 为管理台） |
| MySQL | huizhitong-mysql | 3307 | 业务数据（首次启动自动建表） |

## 前置条件

- Docker Desktop 已运行；
- Java 两个 jar 与前端 `dist` 已构建（下面命令会重新构建）；
- BGE 本地模型目录存在（默认 `E:/develop/Embedding`，可在 `deploy/.env` 覆盖）；
- 有 DeepSeek API Key（不填也能启动，但对话会返回失败提示）。

## 首次部署

```powershell
cd D:\projects\huizhitong-agent

# 1. 构建最新产物（Java 用 JDK 17）
$env:JAVA_HOME = 'C:\Users\王可安然\.jdks\ms-17.0.19'
& cmd /d /c "mvn -q -f java\huizhitong-tool-service\pom.xml package -DskipTests"
& cmd /d /c "mvn -q -f java\huizhitong-gateway\pom.xml package -DskipTests"
cd frontend; npm run build; cd ..

# 2. 配置密钥（编辑 deploy\.env 填入 DEEPSEEK_API_KEY 等）
Copy-Item deploy\.env.example deploy\.env

# 3. 停本地开发服务，避免端口冲突
powershell -ExecutionPolicy Bypass -File scripts\stop-services.ps1

# 4. 构建镜像并启动（首次构建较慢，Agent 镜像含 torch CPU）
docker compose -f deploy\docker-compose.yml build
docker compose -f deploy\docker-compose.yml up -d
```

## 复用宿主机 MySQL（国内网络拉不动 mysql:8.0 时）

本机已有 MySQL 时，可用覆盖文件跳过 mysql:8.0 镜像（约 190MB），直接连宿主机 3306：

```powershell
# 构建镜像时仍用标准编排文件
docker compose -f deploy\docker-compose.yml build

# 启动时叠加 host 覆盖文件：容器版 MySQL 被跳过，服务直连宿主机 MySQL
docker compose -f deploy\docker-compose.yml -f deploy\docker-compose.host.yml up -d
```

要求：宿主机 MySQL 已建 `huizhitong` 库；root 密码写入 `deploy\.env` 的 `MYSQL_HOST_PASSWORD`（默认 henu）。
表由 Java/Python 服务启动时自建（与本地开发共用一套库，数据即开发数据）。
## 国内网络下拉取镜像失败的处理

基础镜像拉不动时，通常是网络无法直连 Docker Hub。推荐做法：

1. 打开 Clash Verge 等代理工具（确保能访问 Docker Hub）；
2. Docker Desktop → Settings → Resources → Proxies → 手动配置：
   `http://127.0.0.1:7897`（HTTP 与 HTTPS 都填），保存后重启 Docker Desktop；
3. 确认生效：`docker info` 应显示 `Proxy=http.docker.internal:3128`；
4. 重新 `docker compose build`，基础镜像与 pip 依赖都会走代理。

验证代理是否真正生效：`curl -x http://127.0.0.1:7897 -I https://registry-1.docker.io/v2/`
返回 401 即代表可达（401 是未带凭证的正常响应）。
## 验证

- 前端控制台：`http://localhost:5173`（默认账号 admin / admin123）
- 健康检查：`curl http://localhost:8080/api/internal/health` 应返回 UP
- RabbitMQ 管理台：`http://localhost:15673`（huizhitong / huizhitong）
- MySQL：宿主机 `localhost:3307`（hzt / 密码见 deploy/.env）

## 切换回本地开发

```powershell
docker compose -f deploy\docker-compose.yml down
powershell -ExecutionPolicy Bypass -File scripts\start-services.ps1
```

## 说明与限制

- RAG 向量存储默认 `memory`（零外部依赖）；要切 Milvus：先启动 `deploy/docker-compose.infra.yml`，
  再把 `deploy/.env` 的 `RAG_VECTOR_STORE` 改为 `milvus`；
- MCP 工具默认关闭（使用内置内存工具实现）；容器内启用 MCP 需要把 `python/mcp-servers` 一并打入
  Agent 镜像（后续增强项）；
- MySQL 数据持久化在 `mysql-data` 卷：`docker compose down` 不删数据，`down -v` 才会清空重建；
- 首次构建耗时较长属正常（Agent 镜像约 2GB+，含 torch CPU 版）。