"""BM25, dense, and hybrid retrieval orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from app.config import Settings, get_settings
from app.retrieval.bm25 import (
    BM25Retriever,
    normalize_legal_unit,
    query_law_codes,
    query_legal_units,
)
from app.retrieval.dense import DenseRetriever
from app.retrieval.embeddings import EmbeddingModel
from app.retrieval.models import ChunkStore, ScoredChunk
from app.retrieval.rerank import CrossEncoderReranker

RetrievalMode = Literal["dense", "bm25", "hybrid"]
RETRIEVAL_MODES: tuple[RetrievalMode, ...] = ("dense", "bm25", "hybrid")


@dataclass(frozen=True)
class IndexStats:
    indexed_chunks: int
    qdrant_points: int
    collection: str
    embedding_model: str
    collection_ready: bool


class RetrievalService:
    def __init__(self, settings: Settings) -> None:
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

    def stats(self) -> IndexStats:
        ready = self._dense.collection_exists()
        return IndexStats(
            indexed_chunks=len(self._store),
            qdrant_points=self._dense.count() if ready else 0,
            collection=self._dense.collection_name,
            embedding_model=self._embedder.model_name,
            collection_ready=ready,
        )

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

    def _dense_search(
        self, query: str, fetch_n: int, law_code: str | None
    ) -> list[tuple[str, float]]:
        vector = self._embedder.encode_query(query)
        return self._dense.search(vector, top_k=fetch_n, law_code=law_code)

    def _bm25_search(
        self, query: str, fetch_n: int, law_code: str | None
    ) -> list[tuple[str, float]]:
        if not law_code:
            return self._bm25.search(query, top_k=fetch_n)

        # BM25 has no metadata filter, so filter a wider result set here.
        raw = self._bm25.search(query, top_k=fetch_n * 5)
        filtered = []
        for chunk_id, score in raw:
            chunk = self._store.get(chunk_id)
            if chunk is not None and chunk.law_code == law_code:
                filtered.append((chunk_id, score))
        return filtered[:fetch_n]

    def _hybrid_search(
        self, query: str, fetch_n: int, law_code: str | None
    ) -> list[tuple[str, float]]:
        dense_ids = [
            chunk_id for chunk_id, _ in self._dense_search(query, self._candidate_pool, law_code)
        ]
        bm25_ids = [
            chunk_id for chunk_id, _ in self._bm25_search(query, self._candidate_pool, law_code)
        ]
        return reciprocal_rank_fusion([dense_ids, bm25_ids], limit=fetch_n)

    def _apply_rerank(
        self, query: str, ranked: list[tuple[str, float]], top_k: int
    ) -> list[tuple[str, float]]:
        candidates = []
        for chunk_id, _ in ranked:
            chunk = self._store.get(chunk_id)
            if chunk is not None:
                candidates.append((chunk_id, chunk.text))
        return self._reranker.rerank(query, candidates, top_k=top_k)

    def _to_scored_chunks(self, ranked: list[tuple[str, float]], method: str) -> list[ScoredChunk]:
        scored: list[ScoredChunk] = []
        for chunk_id, score in ranked:
            chunk = self._store.get(chunk_id)
            if chunk is not None:
                scored.append(ScoredChunk(chunk=chunk, score=score, method=method))
        return scored

    def _prepend_exact_reference_matches(
        self,
        query: str,
        ranked: list[tuple[str, float]],
        law_code: str | None,
    ) -> list[tuple[str, float]]:
        query_units = query_legal_units(query)
        law_codes = query_law_codes(query, [chunk.law_code for chunk in self._store.chunks])
        if law_code:
            law_codes.add(law_code.casefold())
        if not query_units or not law_codes:
            return ranked

        exact_ids = [
            chunk.chunk_id
            for chunk in self._store.chunks
            if chunk.law_code.casefold() in law_codes
            and normalize_legal_unit(chunk.citation) in query_units
        ]
        if not exact_ids:
            return ranked

        seen = set(exact_ids)
        exact = [(chunk_id, 1.0) for chunk_id in exact_ids]
        remainder = [(chunk_id, score) for chunk_id, score in ranked if chunk_id not in seen]
        return exact + remainder


@lru_cache
def get_retrieval_service() -> RetrievalService:
    """Load the index on first use so startup and health checks stay lightweight."""
    return RetrievalService(get_settings())


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
    limit: int = 10,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked_ids in ranked_lists:
        for rank, item_id in enumerate(ranked_ids, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
