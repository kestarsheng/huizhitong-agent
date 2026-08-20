from app.rag.pipeline import RAGRetriever, split_document


class DuplicateDocumentError(ValueError):
    """同一 document_id 重复入库时抛出。"""


class KnowledgeService:
    """知识库服务：维护文档登记、切片入库与检索。"""

    def __init__(self) -> None:
        self.retriever = RAGRetriever()
        self._documents: list[dict[str, object]] = []
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

    def add_document(self, document_id: str, content: str, tenant_id: str = "default") -> list[str]:
        """切片入库并登记文档，返回该文档的 chunk_id 列表。"""
        if any(doc["document_id"] == document_id for doc in self._documents):
            raise DuplicateDocumentError(f"document_id already exists: {document_id}")
        chunks = split_document(document_id, content)
        self.retriever.add(chunks)
        self._documents.append({
            "document_id": document_id,
            "tenant_id": tenant_id,
            "chunk_count": len(chunks),
        })
        return [chunk.chunk_id for chunk in chunks]

    def list_documents(self) -> list[dict[str, object]]:
        return list(self._documents)

    def search_context(self, question: str, top_k: int = 3) -> str:
        results = self.retriever.retrieve(question, top_k=top_k)
        return "\n".join(item.chunk.content for item in results if item.sparse_score > 0)


knowledge_service = KnowledgeService()
