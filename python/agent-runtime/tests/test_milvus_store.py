import pytest

from app.rag.milvus_store import MilvusDocumentStore
from app.rag.models import DocumentChunk


def test_milvus_store_validates_batch_size():
    store = MilvusDocumentStore()
    with pytest.raises(ValueError):
        store.insert([DocumentChunk("1", "text")], [])
