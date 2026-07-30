"""Retrieval service — the single object the API talks to.

Wires the embedding model, Qdrant dense retriever, BM25 index, cross-encoder
reranker, and in-memory chunk store into one `retrieve()` call. Construction is
cheap (BM25 build + Qdrant connection, ~1-2s); the embedding and reranker models
load lazily on first use.

Pipeline for `mode="hybrid"`:

    query ──┬─► dense (Qdrant cosine) ─┐
            └─► BM25 (lexical)        ─┴─► RRF fusion ─► [rerank] ─► top-k
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from app.config import Settings, get_settings
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.dense import DenseRetriever
from app.retrieval.embeddings import EmbeddingModel
from app.retrieval.hybrid import fuse_retrieval_results
from app.retrieval.models import ScoredChunk
from app.retrieval.rerank import CrossEncoderReranker
from app.retrieval.store import ChunkStore

RetrievalMode = Literal["dense", "bm25", "hybrid"]
RETRIEVAL_MODES: tuple[RetrievalMode, ...] = ("dense", "bm25", "hybrid")
_LEGAL_UNIT_RE = re.compile(r"(§+\s*\d+[a-zA-Z]*|art\.?\s*\d+[a-zA-Z]*)", re.IGNORECASE)


@dataclass(frozen=True)
class IndexStats:
    indexed_chunks: int
    qdrant_points: int
    collection: str
    embedding_model: str
    collection_ready: bool


# The orchestrator for search. One instance owns the chunk store,
# the BM25 index, the Qdrant client, the embedding model, and the
# reranker, and exposes them all through a single retrieve()
# call. The rest of the app never touches those parts directly.
class RetrievalService:
    # Build-time wiring. The store + BM25 index are built right away
    # (fast, in memory). The embedding and reranker models are created
    # here but only load their weights on first use, so constructing
    # the service stays cheap (good for tests and /health).
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._candidate_pool = settings.retrieval_candidate_pool
        self._store = ChunkStore.from_jsonl(settings.index_chunks_path)
        self._bm25 = BM25Retriever(self._store.chunks)
        self._dense = DenseRetriever(settings.qdrant_url, settings.qdrant_collection)
        self._embedder = EmbeddingModel(
            settings.embedding_model,
            device=settings.embedding_device,
            batch_size=settings.embedding_batch_size,
        )
        self._reranker = CrossEncoderReranker(
            settings.reranker_model,
            device=settings.embedding_device,
        )

    # Lightweight index report for the /index/stats route: local chunk count
    # plus Qdrant's point count (0 when the collection doesn't exist yet).
    def stats(self) -> IndexStats:
        ready = self._dense.collection_exists()
        return IndexStats(
            indexed_chunks=len(self._store),
            qdrant_points=self._dense.count() if ready else 0,
            collection=self._dense.collection_name,
            embedding_model=self._embedder.model_name,
            collection_ready=ready,
        )

    # The one public search method. Receives the user query plus options and returns
    # a ranked list of ScoredChunk (each = chunk + score + which stage ranked it).
    # Pipeline: choose the stage (dense / bm25 / hybrid) -> pull exact section+law
    # matches to the front -> optionally rerank a deeper pool -> trim to top_k.
    # `fetch_n` is wider than top_k only when reranking, so the cross-encoder has
    # spare candidates to re-sort; otherwise we fetch exactly what we return.
    def retrieve(
        self,
        query: str,
        *,
        mode: RetrievalMode = "hybrid",
        top_k: int = 5,
        rerank: bool = False,
        law_code: str | None = None,
    ) -> list[ScoredChunk]:
        query = query.strip()
        if not query:
            return []

        # When reranking, retrieve a deeper candidate pool so the cross-encoder
        # has something to re-sort; otherwise fetch exactly what we return.
        fetch_n = self._candidate_pool if rerank else top_k

        if mode == "dense":
            ranked = self._dense_search(query, fetch_n, law_code)
        elif mode == "bm25":
            ranked = self._bm25_search(query, fetch_n, law_code)
        else:
            ranked = self._hybrid_search(query, fetch_n, law_code)

        ranked = self._prepend_exact_reference_matches(query, ranked, law_code)

        method: str = mode
        if rerank:
            ranked = self._apply_rerank(query, ranked, top_k)
            method = f"{mode}+rerank"

        return self._to_scored_chunks(ranked[:top_k], method)

    # -- individual retrieval stages ------------------------------------------

    # Dense stage — embed the query into a vector and ask Qdrant for nearest chunks.
    def _dense_search(
        self, query: str, fetch_n: int, law_code: str | None
    ) -> list[tuple[str, float]]:
        vector = self._embedder.encode_query(query)
        return self._dense.search(vector, top_k=fetch_n, law_code=law_code)

    # Lexical stage — exact-term matching. BM25 can't filter by law_code inside its
    # index, so when a law_code is given we over-fetch and filter the hits by hand.
    def _bm25_search(
        self, query: str, fetch_n: int, law_code: str | None
    ) -> list[tuple[str, float]]:
        if not law_code:
            return self._bm25.search(query, top_k=fetch_n)
        # BM25 has no payload filter; over-fetch and post-filter by law code.
        raw = self._bm25.search(query, top_k=fetch_n * 5)
        filtered = [
            (chunk_id, score)
            for chunk_id, score in raw
            if (chunk := self._store.get(chunk_id)) and chunk.law_code == law_code
        ]
        return filtered[:fetch_n]

    # Hybrid stage — run dense + BM25 at full pool depth, then merge
    # their rank positions with RRF (rrf.py). Combining ranks instead
    # of raw scores lets two very different score scales blend fairly.
    def _hybrid_search(
        self, query: str, fetch_n: int, law_code: str | None
    ) -> list[tuple[str, float]]:
        # Fuse at full candidate-pool depth so RRF sees each retriever's tail,
        # then trim to what the caller asked for.
        dense_ids = [
            chunk_id for chunk_id, _ in self._dense_search(query, self._candidate_pool, law_code)
        ]
        bm25_ids = [
            chunk_id for chunk_id, _ in self._bm25_search(query, self._candidate_pool, law_code)
        ]
        return fuse_retrieval_results(dense_ids, bm25_ids, limit=fetch_n)

    # Re-score the candidate pool with the cross-encoder, which reads each (query,
    # chunk) pair together for a sharper relevance score, then keep top_k.
    def _apply_rerank(
        self, query: str, ranked: list[tuple[str, float]], top_k: int
    ) -> list[tuple[str, float]]:
        candidates = [
            (chunk_id, chunk.text)
            for chunk_id, _ in ranked
            if (chunk := self._store.get(chunk_id)) is not None
        ]
        return self._reranker.rerank(query, candidates, top_k=top_k)

    # Hydrate bare (chunk_id, score) pairs back into full ScoredChunk objects
    # via the store; any id not found in the store is silently dropped.
    def _to_scored_chunks(self, ranked: list[tuple[str, float]], method: str) -> list[ScoredChunk]:
        scored: list[ScoredChunk] = []
        for chunk_id, score in ranked:
            chunk = self._store.get(chunk_id)
            if chunk is not None:
                scored.append(ScoredChunk(chunk=chunk, score=score, method=method))
        return scored

    # Precision booster for queries that name a specific section + law,
    # e.g. "§ 433 BGB". When the query mentions BOTH a legal unit (a §/Art
    # number) and a known law code, every chunk matching both exactly is
    # forced to the very top (score 1.0), ahead of the statistical ranking
    # — so the exact article is never buried by fuzzy matches. If there's
    # no such match, the original ranking is returned untouched.
    def _prepend_exact_reference_matches(
        self,
        query: str,
        ranked: list[tuple[str, float]],
        law_code: str | None,
    ) -> list[tuple[str, float]]:
        query_units = _query_legal_units(query)
        query_law_codes = _query_law_codes(query, [chunk.law_code for chunk in self._store.chunks])
        if law_code:
            query_law_codes.add(law_code.casefold())
        if not query_units or not query_law_codes:
            return ranked

        exact_ids = [
            chunk.chunk_id
            for chunk in self._store.chunks
            if chunk.law_code.casefold() in query_law_codes
            and _normalize_legal_unit(chunk.citation) in query_units
        ]
        if not exact_ids:
            return ranked

        seen = set(exact_ids)
        exact = [(chunk_id, 1.0) for chunk_id in exact_ids]
        remainder = [(chunk_id, score) for chunk_id, score in ranked if chunk_id not in seen]
        return exact + remainder


# Process-wide factory. @lru_cache means the heavy
# RetrievalService is built once and reused for every request; the
# docstring explains why failures are deliberately not cached.
@lru_cache
def get_retrieval_service() -> RetrievalService:
    """Process-wide singleton. Built on first request, not at import time, so the
    test suite and `/health` stay fast. Failures (Qdrant down, missing index)
    propagate and are not cached, so a later request can succeed."""
    return RetrievalService(get_settings())


# Small text helpers shared by retrieve() and the booster above:
# - _query_law_codes: codes (BGB, GG, ...) named as whole words in the query.
# - _query_legal_units: section markers (§ 433, Art 5, ...) present in the query.
# - _normalize_legal_unit: canonicalize a marker so "§ 433" and "§433" match.
def _query_law_codes(query: str, law_codes: list[str]) -> set[str]:
    query_folded = query.casefold()
    known_codes = {code.casefold() for code in law_codes if code}
    return {code for code in known_codes if re.search(rf"\b{re.escape(code)}\b", query_folded)}


def _query_legal_units(query: str) -> set[str]:
    return {_normalize_legal_unit(match.group(1)) for match in _LEGAL_UNIT_RE.finditer(query)}


def _normalize_legal_unit(value: str) -> str:
    match = _LEGAL_UNIT_RE.search(value)
    if not match:
        return ""
    unit = match.group(1).casefold().replace(".", "")
    return re.sub(r"\s+", " ", unit).strip()
