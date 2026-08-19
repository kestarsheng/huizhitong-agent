import os
from collections.abc import Sequence

from app.rag.models import DocumentChunk, RetrievedChunk


class MilvusDocumentStore:
    """Milvus 适配层；依赖按需导入，便于单元测试和本地无 Milvus 开发。"""

    def __init__(self, collection_name: str | None = None, uri: str | None = None):
        self.collection_name = collection_name or os.getenv("MILVUS_COLLECTION", "hzt_knowledge_chunks")
        self.uri = uri or os.getenv("MILVUS_URI", "http://localhost:19530")
        self._collection = None

    def _load(self):
        if self._collection is not None:
            return self._collection
        try:
            from pymilvus import Collection, connections
        except ImportError as exc:
            raise RuntimeError("请安装 pymilvus 后再启用 Milvus") from exc
        connections.connect(alias="default", uri=self.uri)
        self._collection = Collection(self.collection_name)
        self._collection.load()
        return self._collection

    def insert(self, chunks: Sequence[DocumentChunk], dense_vectors: Sequence[Sequence[float]]) -> list[str]:
        if len(chunks) != len(dense_vectors):
            raise ValueError("chunks 与 dense_vectors 数量必须一致")
        collection = self._load()
        ids = [item.chunk_id for item in chunks]
        collection.insert([ids, [item.content for item in chunks], [list(vector) for vector in dense_vectors]])
        return ids

    def search_dense(self, vector: Sequence[float], *, top_k: int = 20, tenant_id: str | None = None) -> list[RetrievedChunk]:
        collection = self._load()
        expr = f'tenant_id == "{tenant_id}"' if tenant_id else None
        rows = collection.search([list(vector)], "dense_vector", {"metric_type": "COSINE", "params": {"nprobe": 16}}, limit=top_k, expr=expr, output_fields=["content", "document_id"])[0]
        return [RetrievedChunk(DocumentChunk(str(row.id), row.entity.get("content", ""), {"document_id": row.entity.get("document_id", "")} ), dense_score=float(row.score)) for row in rows]
