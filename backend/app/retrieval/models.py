"""Shared retrieval data structures.

Everything downstream of ingestion is keyed on `chunk_id`. The retrievers
(dense, BM25) return `(chunk_id, score)` pairs; the `ChunkStore` hydrates those
ids into `IndexedChunk`s for API responses and reranking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IndexedChunk:
    """A processed corpus chunk as loaded by the retrieval service."""

    chunk_id: str
    source_id: str
    title: str
    text: str
    citation: str
    law_code: str
    source_url: str
    hierarchy: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_jsonl_record(cls, record: dict[str, Any]) -> IndexedChunk:
        metadata: dict[str, Any] = record.get("metadata", {})
        return cls(
            chunk_id=record["chunk_id"],
            source_id=record["source_id"],
            title=record.get("title", ""),
            text=record["text"],
            citation=str(metadata.get("citation", "")).strip(),
            law_code=str(metadata.get("law_code", "")).strip(),
            source_url=str(metadata.get("source_url", "")).strip(),
            hierarchy=list(metadata.get("hierarchy", [])),
            metadata=metadata,
        )


@dataclass(frozen=True)
class ScoredChunk:
    """A chunk paired with its retrieval score and the stage that produced it."""

    chunk: IndexedChunk
    score: float
    method: str
