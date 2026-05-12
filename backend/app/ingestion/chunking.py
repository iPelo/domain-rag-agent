import re
import unicodedata
from collections.abc import Iterable

from app.ingestion.models import DocumentChunk, RawDocument


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
LEGAL_UNIT_RE = re.compile(r"^(?P<unit>(?:§{1,2}|Art\.?|Artikel)\s+\S+)", re.IGNORECASE)


def chunk_document(
    document: RawDocument,
    *,
    chunk_size: int = 1600,
    overlap: int = 180,
) -> Iterable[DocumentChunk]:
    if document.metadata.get("dataset") == "bundestag/gesetze":
        yield from chunk_german_law_markdown(document, chunk_size=chunk_size, overlap=overlap)
        return

    yield from chunk_text(document, chunk_size=chunk_size, overlap=overlap)


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
            (item_level, item_label)
            for item_level, item_label in hierarchy
            if item_level < level
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
