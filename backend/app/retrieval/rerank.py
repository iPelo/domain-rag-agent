"""Cross-encoder reranking stage.

Bi-encoder retrieval (dense + BM25) scores the query and each chunk
independently, so it is fast but coarse. A cross-encoder reads the
`(query, chunk)` pair jointly and scores relevance directly — much more
accurate, but too slow to run over the whole corpus.

So it runs last: retrieve a candidate pool cheaply, then rerank only those
candidates. The model (`bge-reranker-v2-m3`, ~2GB) is loaded lazily on first
use, so importing this module and running retrieval without `rerank=true`
costs nothing.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


# The final, most accurate ranking stage. A cross-encoder reads the
# query and a chunk TOGETHER and scores their relevance directly —
# sharper than dense/BM25, but too slow to run over the whole corpus,
# so it only re-sorts the small candidate pool from earlier stages.
class CrossEncoderReranker:
    def __init__(
        self,
        model_name: str,
        *,
        device: str | None = None,
        batch_size: int = 16,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._batch_size = batch_size
        self._model: Any = None

    @property
    def model_name(self) -> str:
        return self._model_name

    # Lazy loader — the reranker weights (~2GB) load on first use only, so
    # retrieval without rerank=true (and the whole test suite) pays nothing.
    def _ensure_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name, device=self._device)
        return self._model

    # Re-score (chunk_id, text) candidates against the query
    # and return the best top_k. Empty input short-circuits,
    # which also avoids triggering the lazy model load.
    def rerank(
        self,
        query: str,
        candidates: Sequence[tuple[str, str]],
        *,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Rescore `(chunk_id, text)` candidates; return the top_k by relevance."""
        if not candidates:
            return []
        model = self._ensure_model()
        scores = model.predict(
            [(query, text) for _, text in candidates],
            batch_size=self._batch_size,
        )
        ranked = sorted(
            (
                (chunk_id, float(score))
                for (chunk_id, _), score in zip(candidates, scores, strict=True)
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        return ranked[:top_k]
