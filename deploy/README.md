# 部署编排文件

## 全栈一键部署（MySQL + RabbitMQ + 网关 + 工具服务 + Agent + 前端）

```bash
# 先配置 deploy/.env（从 .env.example 复制并填写 API Key）
cp deploy/.env.example deploy/.env

# 构建并启动
docker compose -f deploy/docker-compose.yml build
docker compose -f deploy/docker-compose.yml up -d
```

复用宿主机 MySQL（省去 mysql:8.0 镜像，适合国内网络）：

```bash
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.host.yml up -d
```

详见 [docs/docker-deploy.md](../docs/docker-deploy.md)。

## 本地基础设施（仅 RAG 用 Milvus 时）

启动 Milvus 及其依赖：

```bash
docker compose -f deploy/docker-compose.infra.yml up -d
```

停止基础设施：

```bash
docker compose -f deploy/docker-compose.infra.yml down
```

Agent Runtime 配置：

```env
RAG_VECTOR_STORE=milvus
MILVUS_URI=http://localhost:19530
```

## 国内镜像拉取辅助

`pull-images.ps1`：镜像源不稳定时，后台重试从多个国内镜像源拉取基础镜像并打回标准 tag，
避免 `docker compose build` 卡在基础镜像下载。