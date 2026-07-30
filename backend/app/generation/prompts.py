"""Prompt construction for grounded answer generation."""

from __future__ import annotations

from app.retrieval.models import ScoredChunk

# This file builds the two pieces of text sent to the chat model for /answer: a
# fixed system instruction (the rules in the string below) and a per-question user
# message (the question + formatted sources). The rules force source-only, cited
# answers.
GROUNDING_SYSTEM_PROMPT = """You answer questions about German federal law texts.

Rules:
- Use only the supplied source chunks.
- If the chunks do not support an answer, say that the retrieved sources do not
  contain enough information.
- Cite every sourced claim with one or more exact chunk IDs in square brackets.
- Do not cite laws or chunk IDs that are not present in the supplied sources.
- Keep the answer concise and practical.
"""


# Assemble the per-question user message: the question followed by
# each retrieved source (numbered, with its chunk_id / citation / url
# / text). Receives the query + ranked chunks and returns one string.
# The exact chunk_ids shown here are what the model must cite back.
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


# Render one numbered source block, truncating very long chunk
# text to keep the request size bounded (max_chars_per_chunk).
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
