import os
from dataclasses import dataclass


@dataclass(frozen=True)
class RAGModelConfig:
    embedding_model_path: str = ""
    reranker_model_path: str = ""
    device: str = "cpu"
    rerank_top_k: int = 5

    @classmethod
    def from_env(cls) -> "RAGModelConfig":
        return cls(
            embedding_model_path=os.getenv("EMBEDDING_MODEL_PATH", ""),
            reranker_model_path=os.getenv("RERANKER_MODEL_PATH", ""),
            device=os.getenv("RAG_DEVICE", "cpu"),
            rerank_top_k=int(os.getenv("RAG_RERANK_TOP_K", "5")),
        )
