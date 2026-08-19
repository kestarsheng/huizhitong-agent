import pytest

from app.rag.models import DocumentChunk, RetrievedChunk
from app.rag.pipeline import RAGRetriever, reciprocal_rank_fusion, split_document


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


def test_rrf_merges_dense_and_sparse_results():
    first = DocumentChunk("1", "库存规则")
    second = DocumentChunk("2", "维修规则")
    results = reciprocal_rank_fusion(
        [RetrievedChunk(first, dense_score=0.9), RetrievedChunk(second, dense_score=0.8)],
        [RetrievedChunk(second, sparse_score=1.0), RetrievedChunk(first, sparse_score=0.2)],
        top_k=2,
    )
    assert {item.chunk.chunk_id for item in results} == {"1", "2"}
    assert all(item.fused_score > 0 for item in results)
