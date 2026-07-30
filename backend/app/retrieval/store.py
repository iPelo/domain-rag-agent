"""In-memory chunk store.

Single source of truth for chunk text and metadata at query time. Qdrant only
stores vectors keyed by chunk id; BM25 needs the raw text. Both hydrate their
`(chunk_id, score)` results back into `IndexedChunk`s through this store.

The curated index is ~15k chunks, so holding it in memory is trivial. A full
178k-chunk build is still only a few hundred MB and fine for a single process.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.retrieval.models import IndexedChunk


# Holds every chunk in memory and indexes them by chunk_id
# (self._by_id) for O(1) lookup. This is the single source of truth for
# chunk TEXT at query time — Qdrant stores only vectors, so dense +
# BM25 hand back ids and this store turns them back into full chunks.
class ChunkStore:
    def __init__(self, chunks: list[IndexedChunk]) -> None:
        self._chunks = chunks
        self._by_id = {chunk.chunk_id: chunk for chunk in chunks}

    # Load the runtime chunk file (one JSON record per line) into IndexedChunks.
    # Fails loudly with a fix-it hint if the file is missing or empty, so a
    # misconfigured index surfaces immediately instead of returning silent empty
    # results.
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

    # Resolve a list of ids to chunks IN ORDER,
    # skipping any id not present in the store.
    def hydrate(self, chunk_ids: list[str]) -> list[IndexedChunk]:
        """Resolve ids to chunks, silently dropping any that are missing."""
        resolved = [self._by_id.get(chunk_id) for chunk_id in chunk_ids]
        return [chunk for chunk in resolved if chunk is not None]
