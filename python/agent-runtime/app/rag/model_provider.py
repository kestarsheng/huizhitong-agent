from collections.abc import Sequence

from app.rag.config import RAGModelConfig
from app.rag.models import RetrievedChunk


class LocalRAGModelProvider:
    """本地 BGE 模型适配器，首次调用时才加载模型。"""

    def __init__(self, config: RAGModelConfig | None = None):
        self.config = config or RAGModelConfig.from_env()
        self._embedding_model = None
        self._reranker_model = None

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not self.config.embedding_model_path:
            raise RuntimeError("EMBEDDING_MODEL_PATH 未配置")
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("请安装 sentence-transformers 后再使用本地 Embedding") from exc
            self._embedding_model = SentenceTransformer(self.config.embedding_model_path, device=self.config.device)
        vectors = self._embedding_model.encode(list(texts), normalize_embeddings=True)
        return vectors.tolist()

    def rerank(self, query: str, candidates: Sequence[RetrievedChunk]) -> list[RetrievedChunk]:
        if not candidates:
            return []
        if not self.config.reranker_model_path:
            raise RuntimeError("RERANKER_MODEL_PATH 未配置")
        if self._reranker_model is None:
            try:
                from FlagEmbedding import FlagReranker
            except ImportError as exc:
                raise RuntimeError("请安装 FlagEmbedding 后再使用本地 Reranker") from exc
            self._reranker_model = FlagReranker(self.config.reranker_model_path, use_fp16=self.config.device != "cpu")
        pairs = [[query, item.chunk.content] for item in candidates]
        scores = self._reranker_model.compute_score(pairs, normalize=True)
        if not isinstance(scores, list):
            scores = [scores]
        ranked = [RetrievedChunk(item.chunk, item.dense_score, item.sparse_score, item.fused_score, float(score))
                  for item, score in zip(candidates, scores)]
        return sorted(ranked, key=lambda item: item.rerank_score, reverse=True)[: self.config.rerank_top_k]
