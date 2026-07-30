from typing import cast

from app.main import app, retrieval_service
from app.retrieval.models import IndexedChunk, ScoredChunk
from app.retrieval.service import IndexStats, RetrievalService
from fastapi.testclient import TestClient


class FakeRetrievalService:
    def stats(self) -> IndexStats:
        return IndexStats(
            indexed_chunks=1,
            qdrant_points=1,
            collection="test_chunks",
            embedding_model="test-model",
            collection_ready=True,
        )

    def retrieve(
        self,
        query: str,
        *,
        mode: str = "hybrid",
        top_k: int = 5,
        rerank: bool = False,
        law_code: str | None = None,
    ) -> list[ScoredChunk]:
        chunk = IndexedChunk(
            chunk_id="german-laws::gg::art-5",
            source_id="german-laws::gg",
            title="Grundgesetz",
            text="Jeder hat das Recht, seine Meinung frei zu äußern.",
            citation="GG Art 5",
            law_code="GG",
            source_url="https://www.gesetze-im-internet.de/gg/art_5.html",
        )
        return [ScoredChunk(chunk=chunk, score=0.9, method=mode)][:top_k]


def fake_retrieval_service() -> RetrievalService:
    return cast(RetrievalService, FakeRetrievalService())


def test_index_stats_endpoint() -> None:
    app.dependency_overrides[retrieval_service] = fake_retrieval_service
    try:
        response = TestClient(app).get("/index/stats")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["indexed_chunks"] == 1
    assert response.json()["collection_ready"] is True


def test_retrieve_endpoint_returns_source_metadata() -> None:
    app.dependency_overrides[retrieval_service] = fake_retrieval_service
    try:
        response = TestClient(app).get(
            "/retrieve",
            params={"q": "Wo ist die Meinungsfreiheit geregelt?", "law_code": "GG"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["chunk_id"] == "german-laws::gg::art-5"
    assert body["results"][0]["citation"] == "GG Art 5"


def test_retrieve_endpoint_validates_short_queries() -> None:
    response = TestClient(app).get("/retrieve", params={"q": "a"})

    assert response.status_code == 422
