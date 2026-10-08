import json

import pytest
from app.config import Settings
from app.retrieval.dense import DenseRetriever
from app.retrieval.service import RetrievalService
from qdrant_client import QdrantClient


@pytest.fixture
def service(tmp_path, monkeypatch):
    records = [
        {
            "chunk_id": "german-laws::gg::art-5",
            "source_id": "german-laws::gg",
            "title": "Grundgesetz",
            "text": "Jeder hat das Recht auf freie Meinungsäußerung.",
            "metadata": {"law_code": "GG", "citation": "GG Art 5"},
        },
        {
            "chunk_id": "german-laws::bgb::sec-433",
            "source_id": "german-laws::bgb",
            "title": "BGB",
            "text": "Der Verkäufer muss die Sache übergeben.",
            "metadata": {"law_code": "BGB", "citation": "BGB § 433"},
        },
        {
            "chunk_id": "german-laws::gg::art-1",
            "source_id": "german-laws::gg",
            "title": "Grundgesetz",
            "text": "Die Würde des Menschen ist unantastbar.",
            "metadata": {"law_code": "GG", "citation": "GG Art 1"},
        },
    ]
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    monkeypatch.setattr(DenseRetriever, "_new_client", lambda self: QdrantClient(":memory:"))
    service = RetrievalService(Settings(_env_file=None, index_chunks_path=path))
    monkeypatch.setattr(service._embedder, "encode_query", lambda query: [1.0, 0.0])

    # Give Art 5 the weakest vector match so explicit-reference boosting is tested.
    service._dense.recreate_collection(dim=2)
    service._dense.upsert(
        chunk_ids=[record["chunk_id"] for record in records],
        vectors=[[0.0, 1.0], [0.8, 0.6], [1.0, 0.0]],
        payloads=[record["metadata"] for record in records],
    )
    yield service
    service._dense._client.close()


@pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid"])
def test_explicit_reference_ranks_first_without_duplicates(service, mode):
    results = service.retrieve("Art. 5 GG", mode=mode, top_k=3)

    assert results[0].chunk.chunk_id == "german-laws::gg::art-5"
    assert len({result.chunk.chunk_id for result in results}) == len(results)
    assert all(result.method == mode for result in results)


@pytest.mark.parametrize("mode", ["bm25", "dense", "hybrid"])
def test_law_filter_keeps_only_matching_sources(service, mode):
    results = service.retrieve("Verkäufer", mode=mode, top_k=3, law_code="BGB")

    assert len(results) == 1
    assert results[0].chunk.law_code == "BGB"


def test_reranking_receives_text_and_sets_result_method(service, monkeypatch):
    received = []

    def rerank(query, candidates, *, top_k):
        received.extend(candidates)
        return [("german-laws::bgb::sec-433", 0.9)][:top_k]

    monkeypatch.setattr(service._reranker, "rerank", rerank)
    results = service.retrieve("Verkäufer", mode="hybrid", top_k=1, rerank=True)

    assert len(received) == 3
    assert ("german-laws::bgb::sec-433", "Der Verkäufer muss die Sache übergeben.") in received
    assert results[0].chunk.chunk_id == "german-laws::bgb::sec-433"
    assert results[0].method == "hybrid+rerank"
