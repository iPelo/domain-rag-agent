"""Prompt construction for grounded answer generation."""

from __future__ import annotations

from app.retrieval.models import ScoredChunk

GROUNDING_SYSTEM_PROMPT = """You answer questions about German federal law texts.

Rules:
- Use only the supplied source chunks.
- If the chunks do not support an answer, say that the retrieved sources do not
  contain enough information.
- Cite every sourced claim with one or more exact chunk IDs in square brackets.
- Do not cite laws or chunk IDs that are not present in the supplied sources.
- Keep the answer concise and practical.
"""


def build_grounded_user_prompt(
    query: str,
    chunks: list[ScoredChunk],
    *,
    max_chars_per_chunk: int = 2400,
) -> str:
    source_blocks = "\n\n".join(
        _format_source(index, chunk, max_chars_per_chunk=max_chars_per_chunk)
        for index, chunk in enumerate(chunks, start=1)
    )
    return f"""Question:
{query}

Sources:
{source_blocks}

Answer with citations using the exact chunk IDs above."""


def _format_source(
    index: int,
    scored: ScoredChunk,
    *,
    max_chars_per_chunk: int,
) -> str:
    chunk = scored.chunk
    text = chunk.text.strip()
    if len(text) > max_chars_per_chunk:
        text = f"{text[:max_chars_per_chunk].rstrip()}..."
    return "\n".join(
        [
            f"Source {index}",
            f"chunk_id: {chunk.chunk_id}",
            f"citation: {chunk.citation}",
            f"title: {chunk.title}",
            f"url: {chunk.source_url}",
            "text:",
            text,
        ]
    )
