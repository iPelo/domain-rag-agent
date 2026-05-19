"""Dense embedding model wrapper.

Thin layer over `sentence-transformers` so the rest of the app never imports it
directly. The model is loaded lazily on first use — importing this module is
cheap, which keeps FastAPI startup and the test suite fast.

`bge-m3` is multilingual (German matters here) and produces 1024-d vectors. We
L2-normalize every embedding so a dot-product search in Qdrant is exactly cosine
similarity.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class EmbeddingModel:
    def __init__(
        self,
        model_name: str,
        *,
        device: str | None = None,
        batch_size: int = 32,
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
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    @property
    def dimension(self) -> int:
        model = self._ensure_model()
        # sentence-transformers renamed this method in v5; support both.
        getter = getattr(model, "get_embedding_dimension", None)
        if getter is None:
            getter = model.get_sentence_embedding_dimension
        return int(getter())

    def encode(
        self,
        texts: Sequence[str],
        *,
        show_progress: bool = False,
    ) -> list[list[float]]:
        """Embed a batch of passages, returning L2-normalized vectors."""
        if not texts:
            return []
        model = self._ensure_model()
        vectors = model.encode(
            list(texts),
            batch_size=self._batch_size,
            normalize_embeddings=True,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        return [[float(value) for value in row] for row in vectors]

    def encode_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        return self.encode([query])[0]
