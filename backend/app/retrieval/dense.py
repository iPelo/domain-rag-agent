"""Dense vector retrieval backed by Qdrant.

Qdrant stores one point per chunk: a normalized `bge-m3` vector plus a small
payload (`chunk_id`, `law_code`) used for hydration and metadata filtering. Chunk
text itself lives in the `ChunkStore`, not the payload, to keep one source of
truth.

Point ids must be ints or UUIDs, so we derive a deterministic UUIDv5 from each
string `chunk_id` — re-running the indexer overwrites points instead of
duplicating them.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from typing import Any

_CHUNK_ID_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")


def point_id_for(chunk_id: str) -> str:
    """Stable Qdrant point id for a chunk id."""
    return str(uuid.uuid5(_CHUNK_ID_NAMESPACE, chunk_id))


class DenseRetriever:
    def __init__(self, qdrant_url: str, collection_name: str) -> None:
        self._qdrant_url = qdrant_url
        self._collection_name = collection_name
        self._client = self._new_client()

    def _new_client(self) -> Any:
        from qdrant_client import QdrantClient

        return QdrantClient(url=self._qdrant_url)

    def reconnect(self) -> None:
        """Recreate the client — used to recover after a Qdrant restart."""
        self._client = self._new_client()

    @property
    def collection_name(self) -> str:
        return self._collection_name

    def collection_exists(self) -> bool:
        return bool(self._client.collection_exists(self._collection_name))

    def count(self) -> int:
        return int(self._client.count(self._collection_name).count)

    def recreate_collection(self, *, dim: int) -> None:
        """Drop and recreate the collection — used by the indexer for a clean build."""
        from qdrant_client.models import Distance, VectorParams

        if self._client.collection_exists(self._collection_name):
            self._client.delete_collection(self._collection_name)
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    def upsert(
        self,
        chunk_ids: Sequence[str],
        vectors: Sequence[Sequence[float]],
        payloads: Sequence[dict[str, Any]],
    ) -> None:
        from qdrant_client.models import PointStruct

        points = [
            PointStruct(
                id=point_id_for(chunk_id),
                vector=list(vector),
                payload={"chunk_id": chunk_id, **payload},
            )
            for chunk_id, vector, payload in zip(chunk_ids, vectors, payloads, strict=True)
        ]
        self._client.upsert(collection_name=self._collection_name, points=points)

    def search(
        self,
        query_vector: Sequence[float],
        *,
        top_k: int = 10,
        law_code: str | None = None,
    ) -> list[tuple[str, float]]:
        """Return `(chunk_id, cosine_score)` for the nearest chunks."""
        query_filter = _law_code_filter(law_code)
        response = self._client.query_points(
            collection_name=self._collection_name,
            query=list(query_vector),
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        )
        results: list[tuple[str, float]] = []
        for point in response.points:
            payload = point.payload or {}
            chunk_id = payload.get("chunk_id")
            if chunk_id:
                results.append((str(chunk_id), float(point.score)))
        return results


def _law_code_filter(law_code: str | None) -> Any:
    if not law_code:
        return None
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    return Filter(must=[FieldCondition(key="law_code", match=MatchValue(value=law_code))])


def iter_batches(items: Sequence[Any], batch_size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), batch_size):
        yield list(items[start : start + batch_size])
