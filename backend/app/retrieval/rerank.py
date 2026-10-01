"""Lazy cross-encoder reranking."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


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

    def _ensure_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self._model_name, device=self._device)
        return self._model

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
