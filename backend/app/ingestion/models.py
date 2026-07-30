from dataclasses import dataclass, field
from typing import Any


# The two core ingestion shapes. `frozen=True` makes them read-only once built.
# RawDocument = one whole source file after loading (full text + metadata).
@dataclass(frozen=True)
class RawDocument:
    source_id: str
    title: str
    text: str
    source_path: str
    metadata: dict[str, Any] = field(default_factory=dict)


# DocumentChunk = one searchable slice of a RawDocument,
# with character offsets (start_char/end_char) back into
# the original text so a chunk can be traced to its source.
@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source_id: str
    title: str
    text: str
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)
