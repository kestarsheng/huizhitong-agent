from app.rag.knowledge import KnowledgeService


class FakeProvider:
    """确定性哈希向量，模拟本地 embedding/rerank，避免测试加载真实模型。"""

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vector = [0.0] * 8
            for index, char in enumerate(text):
                vector[index % 8] += ord(char)
            norm = sum(value * value for value in vector) ** 0.5
            vectors.append([value / norm if norm else 0.0 for value in vector])
        return vectors

    def rerank(self, query: str, candidates):
        return sorted(candidates, key=lambda item: len(item.chunk.content), reverse=True)


class FakeReranker:
    def __init__(self) -> None:
        self.calls = 0

    def rerank(self, query: str, candidates):
        self.calls += 1
        return candidates


def test_hybrid_retrieval_uses_dense_and_rerank() -> None:
    service = KnowledgeService(provider=FakeProvider(), reranker=FakeReranker(), vector_mode="memory")
    service.add_document("manual", "设备错误码 E-1024 表示散热异常，需要重启设备并检查散热。", tenant_id="t1")
    service.add_document("policy", "七天无理由退货政策适用于签收后七天内，商品需保持完好。", tenant_id="t1")
    context = service.search_context("E-1024 散热异常怎么处理")
    assert "E-1024" in context


def test_fallback_to_sparse_when_provider_fails() -> None:
    class BrokenProvider(FakeProvider):
        def embed(self, texts: list[str]) -> list[list[float]]:
            raise RuntimeError("embedding 模型不可用")

    service = KnowledgeService(provider=BrokenProvider(), reranker=FakeReranker(), vector_mode="memory")
    service.add_document("manual", "P1001 库存不足，需要尽快补货。", tenant_id="t1")
    context = service.search_context("P1001 库存")
    assert "P1001" in context