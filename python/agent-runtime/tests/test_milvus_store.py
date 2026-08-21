import pytest

from app.rag.milvus_store import MilvusDocumentStore
from app.rag.models import DocumentChunk


class FakeCollection:
    def __init__(self) -> None:
        self.inserted: list[dict] = []
        self.deleted_exprs: list[str] = []

    def insert(self, rows: list[dict]) -> None:
        self.inserted = list(rows)

    def delete(self, expr: str) -> None:
        self.deleted_exprs.append(expr)


def test_milvus_store_validates_batch_size():
    store = MilvusDocumentStore()
    with pytest.raises(ValueError):
        store.insert([DocumentChunk("1", "text")], [])


def test_milvus_store_insert_builds_rows(monkeypatch):
    store = MilvusDocumentStore(uri="http://localhost:19530", dim=8)
    collection = FakeCollection()
    monkeypatch.setattr(store, "_connect", lambda: collection)
    chunks = [
        DocumentChunk("m1:0", "内容一", {"document_id": "m1"}),
        DocumentChunk("m1:1", "内容二", {"document_id": "m1"}),
    ]
    ids = store.insert(chunks, [[1.0] * 8, [2.0] * 8], tenant_id="t1")
    assert ids == ["m1:0", "m1:1"]
    assert len(collection.inserted) == 2
    assert collection.inserted[0]["chunk_id"] == "m1:0"
    assert collection.inserted[0]["document_id"] == "m1"
    assert collection.inserted[0]["tenant_id"] == "t1"
    assert collection.inserted[0]["dense_vector"] == [1.0] * 8


def test_milvus_store_delete_builds_expr(monkeypatch):
    store = MilvusDocumentStore()
    collection = FakeCollection()
    monkeypatch.setattr(store, "_connect", lambda: collection)
    store.delete_document("doc-1", tenant_id="t1")
    assert collection.deleted_exprs == ['document_id == "doc-1" and tenant_id == "t1"']