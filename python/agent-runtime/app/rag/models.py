from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: DocumentChunk
    dense_score: float = 0.0
    sparse_score: float = 0.0
    fused_score: float = 0.0
    rerank_score: float = 0.0
