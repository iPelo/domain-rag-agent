from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawDocument:
    source_id: str
    title: str
    text: str
    source_path: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source_id: str
    title: str
    text: str
    start_char: int
    end_char: int
    metadata: dict[str, Any] = field(default_factory=dict)
