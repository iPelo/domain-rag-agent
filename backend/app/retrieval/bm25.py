"""Lexical retrieval with BM25.

Dense embeddings miss exact legal anchors — section numbers, abbreviations like
"BGB" or "StPO", the "§" symbol. BM25 is the complement: it ranks by exact term
overlap. The two are fused later via RRF.

The index is built in memory from the curated chunk file at API startup
(~15k chunks, well under a second).
"""

from __future__ import annotations

import re
import unicodedata

from rank_bm25 import BM25Okapi

from app.retrieval.models import IndexedChunk

# Keep "§" as its own token (queries like "§ 433 BGB" depend on it) and split
# everything else on Unicode word boundaries so umlauts survive.
_TOKEN_RE = re.compile(r"§+|\w+", re.UNICODE)
_LEGAL_UNIT_RE = re.compile(r"(§+\s*\d+[a-zA-Z]*|art\.?\s*\d+[a-zA-Z]*)", re.IGNORECASE)
_GERMAN_REPLACEMENTS = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
    }
)


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for raw_token in _TOKEN_RE.findall(text.casefold()):
        tokens.extend(_token_forms(raw_token))
    return tokens


class BM25Retriever:
    def __init__(self, chunks: list[IndexedChunk]) -> None:
        if not chunks:
            raise ValueError("BM25Retriever needs a non-empty chunk list.")
        self._chunks = chunks
        self._chunk_ids = [chunk.chunk_id for chunk in chunks]
        self._index = BM25Okapi([tokenize(_searchable_text(chunk)) for chunk in chunks])

    def search(self, query: str, *, top_k: int = 10) -> list[tuple[str, float]]:
        """Return `(chunk_id, bm25_score)` for the best-matching chunks."""
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        query_law_codes = _query_law_codes(query, self._chunks)
        query_units = _query_legal_units(query)
        scores = self._index.get_scores(query_tokens)
        ranked = sorted(
            (
                (chunk.chunk_id, _boosted_score(chunk, float(score), query_law_codes, query_units))
                for chunk, score in zip(self._chunks, scores, strict=True)
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        return [(chunk_id, float(score)) for chunk_id, score in ranked[:top_k]]


def _token_forms(token: str) -> list[str]:
    if token == "§":
        return [token]

    folded = _fold_german(token)
    forms = [token]
    if folded != token:
        forms.append(folded)

    if folded.isalpha() and len(folded) >= 7:
        forms.extend(folded[:length] for length in range(5, min(len(folded), 10) + 1))

    return list(dict.fromkeys(forms))


def _fold_german(value: str) -> str:
    transliterated = value.translate(_GERMAN_REPLACEMENTS)
    normalized = unicodedata.normalize("NFKD", transliterated)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _searchable_text(chunk: IndexedChunk) -> str:
    return "\n".join(
        [
            chunk.law_code,
            chunk.law_code,
            chunk.citation,
            chunk.citation,
            chunk.title,
            " > ".join(chunk.hierarchy),
            chunk.text,
        ]
    )


def _query_law_codes(query: str, chunks: list[IndexedChunk]) -> set[str]:
    query_folded = query.casefold()
    known_codes = {chunk.law_code.casefold() for chunk in chunks if chunk.law_code}
    return {code for code in known_codes if re.search(rf"\b{re.escape(code)}\b", query_folded)}


def _query_legal_units(query: str) -> set[str]:
    return {_normalize_legal_unit(match.group(1)) for match in _LEGAL_UNIT_RE.finditer(query)}


def _boosted_score(
    chunk: IndexedChunk,
    score: float,
    query_law_codes: set[str],
    query_units: set[str],
) -> float:
    if query_law_codes and chunk.law_code.casefold() in query_law_codes:
        score += 25.0
    if query_units and _normalize_legal_unit(chunk.citation) in query_units:
        score += 25.0
    return score


def _normalize_legal_unit(value: str) -> str:
    match = _LEGAL_UNIT_RE.search(value)
    if not match:
        return ""
    unit = match.group(1).casefold().replace(".", "")
    return re.sub(r"\s+", " ", unit).strip()
