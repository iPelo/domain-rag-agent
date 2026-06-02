from dataclasses import dataclass

from app.retrieval.models import ScoredChunk
from app.retrieval.service import RetrievalMode, RetrievalService


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    citation: str
    law_code: str
    title: str
    text: str
    score: float
    source_url: str
    method: str

    @classmethod
    def from_scored_chunk(cls, scored: ScoredChunk) -> "RetrievedChunk":
        chunk = scored.chunk
        return cls(
            chunk_id=chunk.chunk_id,
            citation=chunk.citation,
            law_code=chunk.law_code,
            title=chunk.title,
            text=chunk.text,
            score=scored.score,
            source_url=chunk.source_url,
            method=scored.method,
        )


class RetrievalTool:
    name = "retrieve"
    description = "Search the German law corpus for source passages."

    def __init__(
        self,
        retrieval_service: RetrievalService,
        *,
        default_mode: RetrievalMode = "hybrid",
        default_top_k: int = 5,
        default_rerank: bool = False,
    ) -> None:
        self._retrieval_service = retrieval_service
        self._default_mode = default_mode
        self._default_top_k = default_top_k
        self._default_rerank = default_rerank

    def __call__(
        self,
        query: str,
        *,
        mode: RetrievalMode | None = None,
        top_k: int | None = None,
        rerank: bool | None = None,
        law_code: str | None = None,
    ) -> list[RetrievedChunk]:
        scored = self._retrieval_service.retrieve(
            query,
            mode=mode or self._default_mode,
            top_k=top_k or self._default_top_k,
            rerank=self._default_rerank if rerank is None else rerank,
            law_code=law_code,
        )
        return [RetrievedChunk.from_scored_chunk(item) for item in scored]
