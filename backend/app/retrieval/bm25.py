"""BM25 retrieval for exact terms and legal references."""

from __future__ import annotations

import re
import unicodedata

from rank_bm25 import BM25Okapi

from app.retrieval.models import IndexedChunk

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
        self._index = BM25Okapi([tokenize(_searchable_text(chunk)) for chunk in chunks])

    def search(self, query: str, *, top_k: int = 10) -> list[tuple[str, float]]:
        """Return `(chunk_id, bm25_score)` for the best-matching chunks."""
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        law_codes = query_law_codes(query, [chunk.law_code for chunk in self._chunks])
        query_units = query_legal_units(query)
        scores = self._index.get_scores(query_tokens)
        ranked = sorted(
            (
                (chunk.chunk_id, _boosted_score(chunk, float(score), law_codes, query_units))
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
    # Repeating citation fields gives them more weight than body text.
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


def query_law_codes(query: str, law_codes: list[str]) -> set[str]:
    query_folded = query.casefold()
    known_codes = {code.casefold() for code in law_codes if code}
    return {code for code in known_codes if re.search(rf"\b{re.escape(code)}\b", query_folded)}


def query_legal_units(query: str) -> set[str]:
    return {normalize_legal_unit(match.group(1)) for match in _LEGAL_UNIT_RE.finditer(query)}


def _boosted_score(
    chunk: IndexedChunk,
    score: float,
    query_law_codes: set[str],
    query_units: set[str],
) -> float:
    if query_law_codes and chunk.law_code.casefold() in query_law_codes:
        score += 25.0
    if query_units and normalize_legal_unit(chunk.citation) in query_units:
        score += 25.0
    return score


def normalize_legal_unit(value: str) -> str:
    match = _LEGAL_UNIT_RE.search(value)
    if not match:
        return ""
    unit = match.group(1).casefold().replace(".", "")
    return re.sub(r"\s+", " ", unit).strip()
