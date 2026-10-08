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
    app.dependency_overrides[retrieval_service] = fake_retrieval_service
    try:
        response = TestClient(app).get("/retrieve", params={"q": "a"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_sample_law_ingestion_to_bm25_api(tmp_path, monkeypatch) -> None:
    from app.config import Settings
    from app.ingestion.pipeline import build_processed_corpus
    from app.retrieval.dense import DenseRetriever
    from qdrant_client import QdrantClient

    law = tmp_path / "german-laws" / "b" / "bgb" / "index.md"
    law.parent.mkdir(parents=True)
    law.write_text(
        "---\nTitle: Bürgerliches Gesetzbuch\njurabk: BGB\nslug: bgb\n---\n"
        "# Bürgerliches Gesetzbuch\n\n"
        "## § 433 Vertragstypische Pflichten beim Kaufvertrag\n\n"
        "Der Verkäufer muss die Sache übergeben. Der Käufer muss den Kaufpreis zahlen.\n\n"
        "## § 242 Leistung nach Treu und Glauben\n\n"
        "Der Schuldner hat die Leistung nach Treu und Glauben zu bewirken.\n",
        encoding="utf-8",
    )
    chunks_path = tmp_path / "chunks.jsonl"
    counts = build_processed_corpus(
        tmp_path / "german-laws",
        chunks_output_path=chunks_path,
        documents_output_path=tmp_path / "documents.jsonl",
    )
    assert counts == (1, 2)

    monkeypatch.setattr(DenseRetriever, "_new_client", lambda self: QdrantClient(":memory:"))
    service = RetrievalService(Settings(_env_file=None, index_chunks_path=chunks_path))
    app.dependency_overrides[retrieval_service] = lambda: service
    try:
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/docs").status_code == 200
            response = client.get(
                "/retrieve",
                params={
                    "q": "Welche Pflichten hat der Käufer nach § 433 BGB?",
                    "mode": "bm25",
                    "law_code": "BGB",
                    "top_k": 1,
                },
            )
            assert response.status_code == 200
            result = response.json()["results"][0]
            assert result["citation"] == "BGB § 433 Vertragstypische Pflichten beim Kaufvertrag"
            assert "Kaufpreis zahlen" in result["text"]
            assert result["source_url"] == "https://www.gesetze-im-internet.de/bgb/"
            assert result["method"] == "bm25"
            assert client.get("/index/stats").json()["indexed_chunks"] == 2
    finally:
        app.dependency_overrides.clear()
        service._dense._client.close()
