from app.rag.config import RAGModelConfig


def test_rag_model_config_reads_environment(monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL_PATH", "E:/develop/Embedding/bge-m3")
    monkeypatch.setenv("RERANKER_MODEL_PATH", "E:/develop/Embedding/bge-reranker-large")
    config = RAGModelConfig.from_env()
    assert config.embedding_model_path.endswith("bge-m3")
    assert config.reranker_model_path.endswith("bge-reranker-large")
