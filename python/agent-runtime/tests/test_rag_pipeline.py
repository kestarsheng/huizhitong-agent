import pytest

from app.rag.pipeline import RAGRetriever, split_document


def test_split_document_keeps_overlap_and_ids():
    chunks = split_document("manual", "库存安全库存规则。" * 20, chunk_size=20, overlap=5)
    assert len(chunks) > 1
    assert chunks[0].chunk_id == "manual:0"
    assert chunks[1].metadata["document_id"] == "manual"


def test_sparse_retrieval_ranks_keyword_match():
    retriever = RAGRetriever(split_document("a", "P1001 库存充足。") + split_document("b", "售后维修流程。"))
    results = retriever.retrieve("P1001 库存", top_k=1)
    assert results[0].chunk.metadata["document_id"] == "a"


def test_invalid_chunk_options():
    with pytest.raises(ValueError):
        split_document("x", "content", chunk_size=10, overlap=10)
