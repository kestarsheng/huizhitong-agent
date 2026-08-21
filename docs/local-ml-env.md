# 本地机器学习环境说明（RAG 混合检索）

## 背景

agent-runtime 的虚拟环境 `hzt-agent-venv`（Python 3.12.13，由本机 conda 环境 edu_rag 创建）只安装应用依赖（FastAPI、LangGraph、LangChain Core 等），**未安装 ML 栈**（numpy / torch / sentence-transformers / FlagEmbedding / pymilvus）。

RAG 混合检索使用本地 BGE 模型：

- Embedding：`E:/develop/Embedding/bge-m3`
- Reranker：`E:/develop/Embedding/bge-reranker-large`

对应的 ML 依赖已完整安装在本机 conda 环境 `E:\develop\Anaconda\envs\edu_rag` 中。

## 桥接方案（仅本机）

在 `hzt-agent-venv/Lib/site-packages/ml_bridge/` 中以目录联接（junction）方式，把 edu_rag site-packages 中 venv 缺失的包指过来，包括 numpy、torch、pandas、datasets、sentence_transformers、FlagEmbedding、pymilvus、sklearn 等。

**关键点：排除 langchain / langgraph / langchain_community / langchain_core 等版本敏感的包**，避免 edu_rag（langchain 1.2.10 / langchain_core 1.5.3）与 venv 自身（langchain_core 0.3.x）冲突，否则会报 `module 'langchain' has no attribute 'debug'`。

`ml_bridge.pth` 负责把 ml_bridge 加入 `sys.path`。

edu_rag 中以单文件存在的依赖（无法目录联接，直接复制到 ml_bridge）：

- `threadpoolctl.py`：sklearn 导入依赖
- `six.py`：pandas 导入依赖

> **注意**：`ml_bridge/` 与 `ml_bridge.pth` 属于本地环境产物，已由 `.gitignore` 的 `hzt-agent-venv/` 规则排除，**不要提交到仓库**。

## 启动 agent-runtime

在 `python/agent-runtime` 目录下，使用 venv 的 Python 启动：

```powershell
$env:TICKET_STORAGE='mysql'
$env:TICKET_MYSQL_HOST='127.0.0.1'
$env:TICKET_MYSQL_PORT='3306'
$env:TICKET_MYSQL_USER='root'
$env:TICKET_MYSQL_PASSWORD='<密码>'
$env:TICKET_MYSQL_DATABASE='huizhitong'
$env:MCP_TICKET_ENABLED='true'
$env:MCP_INVENTORY_ENABLED='true'
$env:DEEPSEEK_API_KEY='<key>'
$env:EMBEDDING_MODEL_PATH='E:/develop/Embedding/bge-m3'
$env:RERANKER_MODEL_PATH='E:/develop/Embedding/bge-reranker-large'
$env:RAG_DEVICE='cpu'
$env:RAG_RERANK_TOP_K='5'

& 'python\agent-runtime\hzt-agent-venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 验证

1. 环境导入自检（ML 栈来自桥接目录，langchain 不应存在，langchain_core/fastapi/mcp 来自 venv）：

```powershell
& 'hzt-agent-venv\Scripts\python.exe' -c "import numpy, torch, sentence_transformers, FlagEmbedding, pymilvus; import langchain_core, fastapi, mcp; import importlib.util as u; print(u.find_spec('langchain'))"
```

2. 知识问答（首次加载模型较慢）：

```http
POST http://127.0.0.1:8000/internal/agents/run
Content-Type: application/json

{"agent_type":"knowledge","conversation_id":"conv-rag-001","tenant_id":1,"message":"设备报错 E-1024 应该怎么处理"}
```

3. 单元测试：

```powershell
& 'hzt-agent-venv\Scripts\python.exe' -m pytest -q
```

## 混合检索链路

1. 稀疏召回：BM25 风格打分，取前 recall_k（20）
2. 稠密召回：BGE-M3 本地向量化，余弦相似度排序
3. 融合：RRF（Reciprocal Rank Fusion）合并两份结果
4. 重排序：BGE-reranker-large 对融合结果打分，取 top_k（默认 5）
5. 任一环节异常自动降级：稠密失败 → 仅稀疏；重排失败 → 使用融合结果
