import logging
import os
from collections.abc import Sequence

from app.rag.models import DocumentChunk, RetrievedChunk

logger = logging.getLogger(__name__)


class MilvusDocumentStore:
    """Milvus 向量存储适配层。

    - 连接与集合懒加载：集合不存在时自动创建（BGE-M3 1024 维，HNSW + COSINE）；
    - 依赖按需导入，本地未安装 pymilvus 或未启动 Milvus 时仅抛错，
      由上层 KnowledgeService 统一降级为内存向量索引；
    - 每次写入同时保留 chunk_id / document_id / tenant_id 标量字段，
      支持按文档删除与按租户过滤检索。
    """

    def __init__(self, collection_name: str | None = None, uri: str | None = None, dim: int | None = None):
        self.collection_name = collection_name or os.getenv("MILVUS_COLLECTION", "hzt_knowledge_chunks")
        self.uri = uri or os.getenv("MILVUS_URI", "http://localhost:19530")
        self.dim = dim or int(os.getenv("MILVUS_DIM", "1024"))
        self._collection = None

    def _connect(self):
        """连接 Milvus 并确保集合存在且已加载；失败时抛出异常。"""
        if self._collection is not None:
            return self._collection
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
        except ImportError as exc:
            raise RuntimeError("请安装 pymilvus 后再启用 Milvus 存储") from exc
        try:
            connections.connect(alias="default", uri=self.uri)
        except Exception as exc:
            raise RuntimeError(f"Milvus 连接失败: {self.uri}") from exc
        if utility.has_collection(self.collection_name, using="default"):
            collection = Collection(self.collection_name)
        else:
            fields = [
                FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, is_primary=True, max_length=255),
                FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=8192),
                FieldSchema(name="dense_vector", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
            ]
            schema = CollectionSchema(fields, description="汇智通 RAG 知识切片")
            collection = Collection(self.collection_name, schema=schema)
            index_params = {"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}}
            collection.create_index("dense_vector", index_params)
            logger.info("已创建 Milvus 集合 %s（dim=%s）", self.collection_name, self.dim)
        collection.load()
        self._collection = collection
        return collection

    def insert(self, chunks: Sequence[DocumentChunk], dense_vectors: Sequence[Sequence[float]], tenant_id: str = "default") -> list[str]:
        """写入切片向量，返回 chunk_id 列表。"""
        if len(chunks) != len(dense_vectors):
            raise ValueError("chunks 与 dense_vectors 数量必须一致")
        if not chunks:
            return []
        collection = self._connect()
        rows = [
            {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.metadata.get("document_id", ""),
                "tenant_id": tenant_id,
                "content": chunk.content,
                "dense_vector": [float(value) for value in vector],
            }
            for chunk, vector in zip(chunks, dense_vectors)
        ]
        collection.insert(rows)
        return [chunk.chunk_id for chunk in chunks]

    def search_dense(self, vector: Sequence[float], *, top_k: int = 20, tenant_id: str | None = None) -> list[RetrievedChunk]:
        """余弦相似度召回，返回携带 chunk_id 与 dense_score 的结果。"""
        collection = self._connect()
        expr = None
        if tenant_id:
            expr = f'tenant_id == "{tenant_id}"'
        rows = collection.search(
            [list(vector)],
            "dense_vector",
            {"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=top_k,
            expr=expr,
            output_fields=["chunk_id"],
        )[0]
        results: list[RetrievedChunk] = []
        for hit in rows:
            chunk_id = str(hit.id)
            if not chunk_id:
                chunk_id = str(hit.entity.get("chunk_id", ""))
            results.append(RetrievedChunk(DocumentChunk(chunk_id, "", {}), dense_score=float(hit.score)))
        return results

    def delete_document(self, document_id: str, tenant_id: str | None = None) -> None:
        """按 document_id（可选叠加 tenant_id）删除向量。"""
        collection = self._connect()
        expr = f'document_id == "{document_id}"'
        if tenant_id:
            expr += f' and tenant_id == "{tenant_id}"'
        collection.delete(expr)

    def count(self) -> int:
        """返回集合内实体数量，同时用作连通性探测。"""
        collection = self._connect()
        return collection.num_entities