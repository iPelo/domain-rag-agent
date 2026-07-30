"""API request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.generation.service import AnswerCitation as AnswerCitationResult
from app.generation.service import AnswerResult
from app.retrieval.models import ScoredChunk
from app.retrieval.service import IndexStats, RetrievalMode


# This file defines the JSON shapes the API sends and receives (Pydantic models).
# They are the public contract: FastAPI validates incoming bodies against them and
# serializes outgoing ones from them. The frontend's types in api.ts mirror these.
# Each `from_*` classmethod adapts an internal dataclass into its API model.
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

    # Adapter: turn an internal ScoredChunk (a retrieval
    # result) into the API shape, rounding the score for a tidy
    # response. Keeps internal types out of the API layer.
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


# The POST /answer body. Field(...) sets validation + docs:
# e.g. top_k is capped at 1..20 here (stricter than /retrieve's
# 1..50) because answering over many chunks is costly.
class AnswerRequest(BaseModel):
    query: str = Field(min_length=2, description="Question to answer from retrieved sources.")
    mode: RetrievalMode = Field(default="hybrid", description="Retrieval strategy.")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to ground on.")
    rerank: bool = Field(
        default=False, description="Use cross-encoder reranking before generation."
    )
    law_code: str | None = Field(default=None, description="Restrict retrieval to one law code.")


class AnswerCitation(BaseModel):
    chunk_id: str
    citation: str
    title: str
    source_url: str

    @classmethod
    def from_result(cls, citation: AnswerCitationResult) -> AnswerCitation:
        return cls(
            chunk_id=citation.chunk_id,
            citation=citation.citation,
            title=citation.title,
            source_url=citation.source_url,
        )


# The /answer reply: the answer text, the validated
# citations, AND the full source chunks behind it — so the UI
# can show citations and let the user inspect the evidence.
class AnswerResponse(BaseModel):
    query: str
    answer: str
    citations: list[AnswerCitation]
    sources: list[RetrievedChunk]
    mode: str
    rerank: bool
    law_code: str | None

    @classmethod
    def from_result(cls, result: AnswerResult) -> AnswerResponse:
        return cls(
            query=result.query,
            answer=result.answer,
            citations=[AnswerCitation.from_result(citation) for citation in result.citations],
            sources=[RetrievedChunk.from_scored_chunk(source) for source in result.sources],
            mode=result.mode,
            rerank=result.rerank,
            law_code=result.law_code,
        )


# The /index/stats reply — mirrors the internal
# IndexStats dataclass for the UI status bar.
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
