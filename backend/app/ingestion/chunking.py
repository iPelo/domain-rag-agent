import re
import unicodedata
from collections.abc import Iterable
from typing import Literal

from app.ingestion.models import DocumentChunk, RawDocument

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
LEGAL_UNIT_RE = re.compile(r"^(?P<unit>(?:§{1,2}|Art\.?|Artikel)\s+\S+)", re.IGNORECASE)

# Tried in order by the recursive splitter: prefer paragraph breaks, then lines,
# then sentences, then words, finally a hard character cut.
RECURSIVE_SEPARATORS: tuple[str, ...] = ("\n\n", "\n", ". ", " ", "")

# "legal-heading" is the production strategy; "fixed" and "recursive" exist for
# the chunking comparison documented in docs/decisions.md.
ChunkingStrategy = Literal["legal-heading", "fixed", "recursive"]


# Stage 2 of ingestion: split each RawDocument into searchable DocumentChunks. This
# dispatcher picks ONE strategy and yields chunks lazily (it's a generator).
# "legal-heading" is the production path; "fixed"/"recursive" exist to benchmark it.
# For the german-laws dataset it routes to the structure-aware splitter further
# down.
def chunk_document(
    document: RawDocument,
    *,
    strategy: ChunkingStrategy = "legal-heading",
    chunk_size: int = 1600,
    overlap: int = 180,
) -> Iterable[DocumentChunk]:
    if strategy == "fixed":
        yield from chunk_text(document, chunk_size=chunk_size, overlap=overlap)
        return
    if strategy == "recursive":
        yield from chunk_recursive(document, chunk_size=chunk_size, overlap=overlap)
        return

    # "legal-heading": structure-aware, dataset-specific. Branch on the dataset
    # here when adding new corpora rather than rewriting the law-specific path.
    if document.metadata.get("dataset") == "bundestag/gesetze":
        yield from chunk_german_law_markdown(document, chunk_size=chunk_size, overlap=overlap)
        return

    yield from chunk_text(document, chunk_size=chunk_size, overlap=overlap)


# "fixed" strategy: cut the text into fixed-size windows that overlap
# by `overlap` characters (the overlap avoids losing context at a
# boundary). Simple, but can cut mid-word. The guard clauses reject
# nonsensical sizes (overlap must be smaller than chunk_size).
def chunk_text(
    document: RawDocument,
    *,
    chunk_size: int = 1200,
    overlap: int = 180,
) -> Iterable[DocumentChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = document.text.strip()
    if not text:
        return

    cursor = 0
    index = 0
    while cursor < len(text):
        end = min(cursor + chunk_size, len(text))
        chunk_body = text[cursor:end].strip()
        if chunk_body:
            yield DocumentChunk(
                chunk_id=f"{document.source_id}::chunk-{index:05d}",
                source_id=document.source_id,
                title=document.title,
                text=chunk_body,
                start_char=cursor,
                end_char=end,
                metadata=document.metadata,
            )
        if end == len(text):
            break
        cursor = end - overlap
        index += 1


# "recursive" strategy: split on a separator hierarchy (paragraph
# -> line -> sentence -> word) so cuts fall on natural
# boundaries. A middle-ground baseline; see the docstring below.
def chunk_recursive(
    document: RawDocument,
    *,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> Iterable[DocumentChunk]:
    """Split on a separator hierarchy (paragraph -> line -> sentence -> word).

    Unlike fixed-size chunking this avoids cutting mid-sentence, and unlike
    legal-heading chunking it needs no structural markup — a useful baseline for
    the comparison in docs/decisions.md.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    text = document.text.strip()
    if not text:
        return

    segments = _recursive_segments(
        text,
        base=0,
        separators=RECURSIVE_SEPARATORS,
        chunk_size=chunk_size,
    )
    for index, packed in enumerate(
        _pack_segments(segments, chunk_size=chunk_size, overlap=overlap)
    ):
        body = " ".join(segment for segment, _ in packed).strip()
        if not body:
            continue
        start = packed[0][1]
        end = packed[-1][1] + len(packed[-1][0])
        yield DocumentChunk(
            chunk_id=f"{document.source_id}::recursive-{index:05d}",
            source_id=document.source_id,
            title=document.title,
            text=body,
            start_char=start,
            end_char=end,
            metadata={**document.metadata, "chunking_strategy": "recursive"},
        )


# Recursively break text into pieces no bigger than chunk_size,
# only descending to a finer separator when a piece is still
# too large. Returns (segment, absolute_start) pairs.
def _recursive_segments(
    text: str,
    *,
    base: int,
    separators: tuple[str, ...],
    chunk_size: int,
) -> list[tuple[str, int]]:
    """Break text into `(segment, absolute_start)` pieces no larger than
    chunk_size, descending the separator hierarchy only as far as needed."""
    if len(text) <= chunk_size or not separators:
        return [(text, base)]

    separator, *rest = separators
    if separator == "":
        return [
            (text[offset : offset + chunk_size], base + offset)
            for offset in range(0, len(text), chunk_size)
        ]

    segments: list[tuple[str, int]] = []
    offset = 0
    for piece in text.split(separator):
        if piece:
            if len(piece) <= chunk_size:
                segments.append((piece, base + offset))
            else:
                segments.extend(
                    _recursive_segments(
                        piece,
                        base=base + offset,
                        separators=tuple(rest),
                        chunk_size=chunk_size,
                    )
                )
        offset += len(piece) + len(separator)
    return segments


# Greedily glue small segments back into chunks up to chunk_size, carrying
# a little overlap from the end of one chunk into the start of the next.
def _pack_segments(
    segments: list[tuple[str, int]],
    *,
    chunk_size: int,
    overlap: int,
) -> list[list[tuple[str, int]]]:
    """Greedily merge consecutive segments into bounded overlapping windows."""

    def joined_length(items: list[tuple[str, int]]) -> int:
        return sum(len(segment) for segment, _ in items) + max(0, len(items) - 1)

    chunks: list[list[tuple[str, int]]] = []
    current: list[tuple[str, int]] = []
    for segment in segments:
        if current and joined_length([*current, segment]) > chunk_size:
            chunks.append(current)
            current = _trailing_overlap(current, overlap)
            while current and joined_length([*current, segment]) > chunk_size:
                current.pop(0)
        current.append(segment)
    if current:
        chunks.append(current)
    return chunks


def _trailing_overlap(
    items: list[tuple[str, int]],
    overlap: int,
) -> list[tuple[str, int]]:
    carry: list[tuple[str, int]] = []

    def joined_length(values: list[tuple[str, int]]) -> int:
        return sum(len(segment) for segment, _ in values) + max(0, len(values) - 1)

    for item in reversed(items):
        candidate = [item, *carry]
        if joined_length(candidate) > overlap:
            break
        carry.insert(0, item)
    return carry


# "legal-heading" strategy (production): walk the markdown headings (#, ##,
# ### ...) and make one chunk per section, so a chunk lines up with a real
# legal unit (e.g. "§ 433"). It tracks the heading hierarchy (parent > child)
# and stamps each chunk with metadata used later for citations: law_code, the
# heading, the hierarchy, and a citation string. Over-long sections are split
# further, and chunk_ids are de-duplicated so they stay unique.
def chunk_german_law_markdown(
    document: RawDocument,
    *,
    chunk_size: int = 1600,
    overlap: int = 180,
) -> Iterable[DocumentChunk]:
    text = document.text.strip()
    headings = list(_iter_headings(text))
    if not headings:
        yield from chunk_text(document, chunk_size=chunk_size, overlap=overlap)
        return

    emitted = 0
    hierarchy: list[tuple[int, str]] = []
    seen_chunk_ids: set[str] = set()

    for index, heading in enumerate(headings):
        level, label, start, end = heading
        next_start = headings[index + 1][2] if index + 1 < len(headings) else len(text)
        section_body = text[end:next_start].strip()
        hierarchy = [
            (item_level, item_label) for item_level, item_label in hierarchy if item_level < level
        ]
        hierarchy.append((level, label))

        if not section_body:
            continue

        context = [item_label for item_level, item_label in hierarchy if item_level > 1]
        context_label = " > ".join(context)
        text_with_context = f"{context_label}\n\n{section_body}" if context_label else section_body
        slug = _slugify(label) or f"section-{emitted:05d}"
        base_metadata = {
            **document.metadata,
            "heading": label,
            "heading_level": level,
            "hierarchy": context,
            "legal_unit": _legal_unit(label),
            "citation": _citation(document.metadata.get("law_code"), label),
            "chunking_strategy": "legal-heading",
        }

        for split_index, split_text in enumerate(
            _split_text(text_with_context, chunk_size=chunk_size, overlap=overlap)
        ):
            chunk_id = _unique_chunk_id(
                f"{document.source_id}::{slug}",
                seen_chunk_ids,
                split_index=split_index,
            )
            yield DocumentChunk(
                chunk_id=chunk_id,
                source_id=document.source_id,
                title=document.title,
                text=split_text,
                start_char=start,
                end_char=next_start,
                metadata={**base_metadata, "split_index": split_index},
            )

        emitted += 1


def _iter_headings(text: str) -> Iterable[tuple[int, str, int, int]]:
    for match in HEADING_RE.finditer(text):
        yield len(match.group(1)), match.group(2).strip(), match.start(), match.end()


def _split_text(text: str, *, chunk_size: int, overlap: int) -> Iterable[str]:
    if len(text) <= chunk_size:
        yield text
        return

    pseudo_doc = RawDocument(
        source_id="split",
        title="split",
        text=text,
        source_path="",
    )
    for chunk in chunk_text(pseudo_doc, chunk_size=chunk_size, overlap=overlap):
        yield chunk.text


def _unique_chunk_id(base_id: str, seen_chunk_ids: set[str], *, split_index: int) -> str:
    candidate = f"{base_id}-part-{split_index + 1:02d}" if split_index else base_id
    if candidate not in seen_chunk_ids:
        seen_chunk_ids.add(candidate)
        return candidate

    duplicate_index = 2
    while f"{candidate}-{duplicate_index}" in seen_chunk_ids:
        duplicate_index += 1
    unique_id = f"{candidate}-{duplicate_index}"
    seen_chunk_ids.add(unique_id)
    return unique_id


def _legal_unit(heading: str) -> str:
    match = LEGAL_UNIT_RE.match(heading)
    if match:
        return match.group("unit")
    return heading


def _citation(law_code: object, heading: str) -> str:
    prefix = str(law_code) if law_code else ""
    return f"{prefix} {heading}".strip()


# Make a filesystem/url-safe id fragment from a heading: map
# §/Art to words, drop accents, lowercase, and collapse
# everything else to hyphens. Used to build readable chunk ids.
def _slugify(value: str) -> str:
    normalized = (
        value.replace("§§", "sections")
        .replace("§", "sec")
        .replace("Art.", "art")
        .replace("Art ", "art ")
        .replace("Artikel", "artikel")
    )
    normalized = unicodedata.normalize("NFKD", normalized)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug[:96].strip("-")
