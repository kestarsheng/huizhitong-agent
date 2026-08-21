from app.rag.knowledge import KnowledgeService


class FakeProvider:
    """确定性哈希向量，避免测试加载真实模型。"""

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
        return candidates


class BrokenMilvus:
    """模拟 Milvus 不可用：探测与写入均抛错。"""

    uri = "http://localhost:19530"

    def count(self) -> int:
        raise RuntimeError("Milvus 未启动")

    def insert(self, *args, **kwargs):
        raise RuntimeError("Milvus 未启动")

    def search_dense(self, *args, **kwargs):
        raise RuntimeError("Milvus 未启动")


def test_milvus_down_falls_back_to_memory():
    service = KnowledgeService(
        provider=FakeProvider(),
        reranker=FakeProvider(),
        vector_mode="milvus",
        milvus_store=BrokenMilvus(),
    )
    service.add_document("manual", "E-1024 表示散热异常，需要重启设备并检查散热。", tenant_id="t1")
    context = service.search_context("E-1024 散热异常怎么处理")
    assert "E-1024" in context


def test_memory_mode_never_touches_milvus():
    service = KnowledgeService(provider=FakeProvider(), reranker=FakeProvider(), vector_mode="memory")
    service.add_document("manual", "P1001 库存不足，需要尽快补货。", tenant_id="t1")
    context = service.search_context("P1001 库存")
    assert "P1001" in context