import logging
import os

from app.rag.milvus_store import MilvusDocumentStore
from app.rag.model_provider import LocalRAGModelProvider
from app.rag.models import DocumentChunk, RetrievedChunk
from app.rag.pipeline import RAGRetriever, reciprocal_rank_fusion, sparse_score, split_document
from app.rag.reranker import Reranker

logger = logging.getLogger(__name__)


class DuplicateDocumentError(ValueError):
    """同一 document_id 重复入库时抛出。"""


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(x * y for x, y in zip(left, right))
    norm_left = sum(x * x for x in left) ** 0.5
    norm_right = sum(x * x for x in right) ** 0.5
    if norm_left == 0 or norm_right == 0:
        return 0.0
    return dot / (norm_left * norm_right)


class KnowledgeService:
    """知识库服务：文档登记、切片入库，以及稠密+稀疏+重排序的混合检索。

    - 稠密向量默认使用本地 BGE-M3（按需加载，16 条一批向量化）；
    - 支持 Milvus 向量库（RAG_VECTOR_STORE=auto|milvus|memory）：
      Milvus 可用时稠密召回走 Milvus；不可用时自动降级为内存向量索引。
      内存索引始终镜像全部切片，保证降级不丢数据；
    - embedding / reranker 模型不可用时自动降级为纯稀疏检索，链路始终可用。
    """

    def __init__(
        self,
        provider: LocalRAGModelProvider | None = None,
        reranker: Reranker | None = None,
        *,
        vector_mode: str | None = None,
        milvus_store: MilvusDocumentStore | None = None,
    ) -> None:
        self.retriever = RAGRetriever()
        self._documents: list[dict[str, object]] = []
        self._chunks: list[DocumentChunk] = []
        self._chunk_index: dict[str, int] = {}
        self._vectors: list[list[float]] | None = None
        self._provider = provider or LocalRAGModelProvider()
        self._reranker = reranker or Reranker(self._provider)
        self._vector_mode = (vector_mode or os.getenv("RAG_VECTOR_STORE", "auto")).lower()
        self._milvus: MilvusDocumentStore | None = None
        self._milvus_ok: bool | None = None
        if self._vector_mode in ("auto", "milvus"):
            self._milvus = milvus_store or MilvusDocumentStore()
        self.add_document(
            "equipment-manual",
            "设备故障排查：先确认电源和网络连接，再查看设备错误码。若错误码为 E-1024，重启设备并检查散热；问题仍未解决时提交维修工单。",
            tenant_id="default",
        )
        self.add_document(
            "after-sales-policy",
            "售后规则：在保修期内的设备可提交免费维修申请，提交时需要填写设备序列号、故障现象和联系方式。",
            tenant_id="default",
        )

    # ---------- 写入 ----------

    def add_document(self, document_id: str, content: str, tenant_id: str = "default") -> list[str]:
        """切片入库并登记文档，返回该文档的 chunk_id 列表。"""
        if any(doc["document_id"] == document_id for doc in self._documents):
            raise DuplicateDocumentError(f"document_id already exists: {document_id}")
        chunks = split_document(document_id, content)
        base = len(self._chunks)
        self._chunks.extend(chunks)
        self._chunk_index.update({chunk.chunk_id: base + offset for offset, chunk in enumerate(chunks)})
        self.retriever.add(chunks)
        self._vectors = None  # 内存向量缓存失效，下次检索时重建
        self._documents.append({
            "document_id": document_id,
            "tenant_id": tenant_id,
            "chunk_count": len(chunks),
        })
        if self._milvus is not None and self._probe_milvus():
            try:
                vectors = self._embed([chunk.content for chunk in chunks])
                self._milvus.insert(chunks, vectors, tenant_id=tenant_id)
            except Exception as exc:
                self._milvus_ok = False
                logger.warning("Milvus 写入失败，降级为内存向量索引: %s", exc)
        return [chunk.chunk_id for chunk in chunks]

    def list_documents(self) -> list[dict[str, object]]:
        return list(self._documents)

    # ---------- 检索 ----------

    def search_context(self, question: str, top_k: int = 3) -> str:
        try:
            results = self._hybrid_retrieve(question, top_k=top_k)
        except Exception as exc:  # 模型缺失或加载失败时降级
            logger.warning("RAG 混合检索不可用，降级为稀疏检索: %s", exc)
            results = self.retriever.retrieve(question, top_k=top_k)
        relevant = [
            item.chunk.content
            for item in results
            if item.dense_score > 0 or item.sparse_score > 0 or item.fused_score > 0 or item.rerank_score > 0
        ]
        return "\n".join(relevant)

    def _hybrid_retrieve(self, question: str, *, top_k: int = 3, recall_k: int = 20) -> list[RetrievedChunk]:
        if not self._chunks:
            return []
        sparse = sorted(
            (RetrievedChunk(chunk, sparse_score=sparse_score(question, chunk.content)) for chunk in self._chunks),
            key=lambda item: item.sparse_score,
            reverse=True,
        )
        sparse = [item for item in sparse if item.sparse_score > 0][:recall_k]
        try:
            dense = self._dense_recall(question, recall_k=recall_k)
        except Exception as exc:
            logger.warning("稠密召回不可用，仅使用稀疏召回: %s", exc)
            return sparse[:top_k]
        if not dense:
            return sparse[:top_k]
        fused = reciprocal_rank_fusion(dense, sparse, top_k=recall_k)
        try:
            return self._reranker.rerank(question, fused)[:top_k]
        except Exception as exc:
            logger.warning("重排序不可用，使用融合排序结果: %s", exc)
            return fused[:top_k]

    def _dense_recall(self, question: str, *, recall_k: int = 20) -> list[RetrievedChunk]:
        """稠密召回：优先 Milvus，失败或未启用时回退内存索引。"""
        if self._milvus is not None and self._milvus_ok:
            try:
                query_vector = self._provider.embed([question])[0]
                ranked = [
                    RetrievedChunk(self._chunks[index], dense_score=item.dense_score)
                    for item in self._milvus.search_dense(query_vector, top_k=recall_k)
                    if (index := self._chunk_index.get(item.chunk.chunk_id)) is not None
                ]
                if ranked:
                    return ranked
            except Exception as exc:
                self._milvus_ok = False
                logger.warning("Milvus 检索失败，降级为内存向量索引: %s", exc)
        return self._dense_recall_memory(question, recall_k=recall_k)

    def _dense_recall_memory(self, question: str, *, recall_k: int = 20) -> list[RetrievedChunk]:
        if self._vectors is None:
            self._vectors = self._embed([chunk.content for chunk in self._chunks])
        query_vector = self._provider.embed([question])[0]
        ranked = sorted(
            ((index, cosine_similarity(query_vector, vector)) for index, vector in enumerate(self._vectors)),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return [
            RetrievedChunk(self._chunks[index], dense_score=score)
            for index, score in ranked[:recall_k]
            if score > 0
        ]

    # ---------- 内部 ----------

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), 16):
            vectors.extend(self._provider.embed(texts[start:start + 16]))
        return vectors

    def _probe_milvus(self) -> bool:
        """探测 Milvus 可用性；失败后整个会话保持降级，避免反复重连。"""
        if self._milvus is None:
            return False
        if self._milvus_ok is not None:
            return self._milvus_ok
        try:
            self._milvus.count()
            self._milvus_ok = True
            logger.info("Milvus 向量存储可用: %s", self._milvus.uri)
        except Exception as exc:
            self._milvus_ok = False
            logger.warning("Milvus 不可用（%s），本次会话降级为内存向量索引", exc)
        return self._milvus_ok


knowledge_service = KnowledgeService()