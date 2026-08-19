# 本地基础设施

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
MILVUS_URI=http://localhost:19530
```
