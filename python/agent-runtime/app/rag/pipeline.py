import re
from collections import Counter

from app.rag.models import DocumentChunk, RetrievedChunk


def split_document(document_id: str, text: str, *, chunk_size: int = 500, overlap: int = 80) -> list[DocumentChunk]:
    """按字符窗口切片，保留可追溯的 chunk_id。"""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be smaller than chunk_size")
    normalized = re.sub(r"\s+", " ", text).strip()
    chunks: list[DocumentChunk] = []
    start = 0
    index = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunks.append(DocumentChunk(f"{document_id}:{index}", normalized[start:end], {"document_id": document_id}))
        if end == len(normalized):
            break
        start = end - overlap
        index += 1
    return chunks


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]", text.lower())


def sparse_score(query: str, content: str) -> float:
    query_tokens = Counter(_tokens(query))
    content_tokens = Counter(_tokens(content))
    if not query_tokens:
        return 0.0
    return sum(min(count, content_tokens[token]) for token, count in query_tokens.items()) / sum(query_tokens.values())


def fuse_results(chunks: list[DocumentChunk], query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
    """当前为可运行的稀疏基线；dense_score 由 Milvus 适配层填充。"""
    results = [RetrievedChunk(chunk, sparse_score=sparse_score(query, chunk.content)) for chunk in chunks]
    results.sort(key=lambda item: item.sparse_score, reverse=True)
    return results[:top_k]


def reciprocal_rank_fusion(
    dense_results: list[RetrievedChunk],
    sparse_results: list[RetrievedChunk],
    *,
    top_k: int = 20,
    k: int = 60,
) -> list[RetrievedChunk]:
    """使用 RRF 合并两路召回，降低单一路径排序偏差。"""
    merged: dict[str, RetrievedChunk] = {}
    scores: dict[str, float] = {}
    for ranking in (dense_results, sparse_results):
        for rank, item in enumerate(ranking, start=1):
            key = item.chunk.chunk_id
            previous = merged.get(key)
            merged[key] = item if previous is None else RetrievedChunk(
                item.chunk,
                dense_score=max(previous.dense_score, item.dense_score),
                sparse_score=max(previous.sparse_score, item.sparse_score),
            )
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
    return [
        RetrievedChunk(item.chunk, item.dense_score, item.sparse_score, scores[key])
        for key, item in sorted(merged.items(), key=lambda pair: scores[pair[0]], reverse=True)[:top_k]
    ]


class RAGRetriever:
    def __init__(self, chunks: list[DocumentChunk] | None = None):
        self._chunks = chunks or []

    def add(self, chunks: list[DocumentChunk]) -> None:
        self._chunks.extend(chunks)

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievedChunk]:
        return fuse_results(self._chunks, query, top_k=top_k)
