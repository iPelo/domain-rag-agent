"""API request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.retrieval.models import ScoredChunk
from app.retrieval.service import IndexStats


class RetrievedChunk(BaseModel):
    chunk_id: str
    citation: str = Field(description="Human-readable source, e.g. 'GG Art 5'.")
    law_code: str
    title: str
    hierarchy: list[str] = Field(description="Parent headings, outermost first.")
    source_url: str
    score: float
    method: str = Field(description="Retrieval stage that produced this result.")
    text: str

    @classmethod
    def from_scored_chunk(cls, scored: ScoredChunk) -> RetrievedChunk:
        chunk = scored.chunk
        return cls(
            chunk_id=chunk.chunk_id,
            citation=chunk.citation,
            law_code=chunk.law_code,
            title=chunk.title,
            hierarchy=chunk.hierarchy,
            source_url=chunk.source_url,
            score=round(scored.score, 6),
            method=scored.method,
            text=chunk.text,
        )


class RetrieveResponse(BaseModel):
    query: str
    mode: str
    rerank: bool
    law_code: str | None
    count: int
    results: list[RetrievedChunk]


class IndexStatsResponse(BaseModel):
    collection: str
    collection_ready: bool
    indexed_chunks: int
    qdrant_points: int
    embedding_model: str

    @classmethod
    def from_stats(cls, stats: IndexStats) -> IndexStatsResponse:
        return cls(
            collection=stats.collection,
            collection_ready=stats.collection_ready,
            indexed_chunks=stats.indexed_chunks,
            qdrant_points=stats.qdrant_points,
            embedding_model=stats.embedding_model,
        )
