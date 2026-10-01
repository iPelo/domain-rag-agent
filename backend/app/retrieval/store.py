"""In-memory lookup for indexed chunk text and metadata."""

from __future__ import annotations

import json
from pathlib import Path

from app.retrieval.models import IndexedChunk


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
