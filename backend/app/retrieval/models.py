"""Shared retrieval data structures."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
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


class ChunkStore:
    def __init__(self, chunks: list[IndexedChunk]) -> None:
        self._chunks = chunks
        self._by_id = {chunk.chunk_id: chunk for chunk in chunks}

    @classmethod
    def from_jsonl(cls, path: Path) -> ChunkStore:
        if not path.exists():
            raise FileNotFoundError(
                f"Chunk file {path} not found. Run `make index` to build it first."
            )
        chunks: list[IndexedChunk] = []
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    chunks.append(IndexedChunk.from_jsonl_record(json.loads(line)))
        if not chunks:
            raise ValueError(f"Chunk file {path} is empty.")
        return cls(chunks)

    def __len__(self) -> int:
        return len(self._chunks)

    @property
    def chunks(self) -> list[IndexedChunk]:
        return self._chunks

    def get(self, chunk_id: str) -> IndexedChunk | None:
        return self._by_id.get(chunk_id)

    def hydrate(self, chunk_ids: list[str]) -> list[IndexedChunk]:
        """Resolve ids to chunks, silently dropping any that are missing."""
        resolved = [self._by_id.get(chunk_id) for chunk_id in chunk_ids]
        return [chunk for chunk in resolved if chunk is not None]
