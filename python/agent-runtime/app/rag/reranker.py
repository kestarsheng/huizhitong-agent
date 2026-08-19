from collections.abc import Sequence

from app.rag.model_provider import LocalRAGModelProvider
from app.rag.models import RetrievedChunk


class Reranker:
    def __init__(self, provider: LocalRAGModelProvider | None = None):
        self.provider = provider or LocalRAGModelProvider()

    def rerank(self, query: str, candidates: Sequence[RetrievedChunk]) -> list[RetrievedChunk]:
        return self.provider.rerank(query, candidates)
