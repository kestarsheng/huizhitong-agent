from app.rag.pipeline import RAGRetriever, split_document


class KnowledgeService:
    """知识库服务基线；后续可将 chunks 替换为 Milvus 查询结果。"""

    def __init__(self):
        self.retriever = RAGRetriever()
        self.retriever.add(split_document(
            "equipment-manual",
            "设备故障排查：先确认电源和网络连接，再查看设备错误码。若错误码为 E-1024，重启设备并检查散热；问题仍未解决时提交维修工单。",
        ))
        self.retriever.add(split_document(
            "after-sales-policy",
            "售后规则：在保修期内的设备可提交免费维修申请，提交时需要填写设备序列号、故障现象和联系方式。",
        ))

    def search_context(self, question: str, top_k: int = 3) -> str:
        results = self.retriever.retrieve(question, top_k=top_k)
        return "\n".join(item.chunk.content for item in results if item.sparse_score > 0)


knowledge_service = KnowledgeService()
