import json

import pytest
from app.retrieval.bm25 import BM25Retriever, tokenize
from app.retrieval.dense import point_id_for
from app.retrieval.embeddings import EmbeddingModel
from app.retrieval.hybrid import fuse_retrieval_results
from app.retrieval.models import IndexedChunk
from app.retrieval.rerank import CrossEncoderReranker
from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.store import ChunkStore


def _chunk(chunk_id: str, text: str, law: str = "GG") -> IndexedChunk:
    return IndexedChunk(
        chunk_id=chunk_id,
        source_id="german-laws::test",
        title="Test",
        text=text,
        citation=f"{law} {chunk_id}",
        law_code=law,
        source_url="https://example.test/",
    )


# -- tokenization & BM25 ------------------------------------------------------


def test_tokenize_keeps_section_symbol_and_lowercases() -> None:
    tokens = tokenize("§ 433 BGB Meinungsfreiheit")
    assert "§" in tokens
    assert "433" in tokens
    assert "bgb" in tokens
    assert "meinungsfreiheit" in tokens


def test_tokenize_adds_german_ascii_forms_and_prefixes() -> None:
    tokens = tokenize("Kündigung verjaehren")

    assert "kuendigung" in tokens
    assert "verjaehr" in tokens


def test_bm25_ranks_exact_term_match_first() -> None:
    chunks = [
        _chunk("a", "Notwehr ist die Verteidigung gegen einen Angriff."),
        _chunk("b", "Der Kaufvertrag verpflichtet den Verkaeufer zur Uebergabe."),
        _chunk("c", "Die Meinungsfreiheit ist im Grundgesetz gewaehrleistet."),
    ]
    results = BM25Retriever(chunks).search("Notwehr", top_k=3)
    assert results[0][0] == "a"


def test_bm25_uses_law_code_and_citation_metadata() -> None:
    chunks = [
        _chunk("german-laws::bgb::sec-242", "Leistung nach Treu und Glauben", "BGB"),
        _chunk("german-laws::stgb::sec-242", "Diebstahl", "StGB"),
        _chunk("german-laws::stpo::sec-242", "Zulässigkeit von Fragen", "StPO"),
    ]
    results = BM25Retriever(chunks).search("§ 242 StGB", top_k=3)

    assert results[0][0] == "german-laws::stgb::sec-242"


def test_bm25_empty_query_returns_nothing() -> None:
    retriever = BM25Retriever([_chunk("a", "irgendein Text")])
    assert retriever.search("   ") == []


def test_bm25_requires_a_non_empty_corpus() -> None:
    with pytest.raises(ValueError):
        BM25Retriever([])


# -- reciprocal rank fusion ---------------------------------------------------


def test_rrf_rewards_results_both_retrievers_agree_on() -> None:
    fused = reciprocal_rank_fusion([["x", "y", "z"], ["x", "z", "y"]], limit=3)
    assert fused[0][0] == "x"


def test_rrf_unions_disjoint_lists() -> None:
    fused = reciprocal_rank_fusion([["a"], ["b"]], limit=5)
    assert {item_id for item_id, _ in fused} == {"a", "b"}


def test_fuse_retrieval_results_merges_dense_and_bm25() -> None:
    fused = fuse_retrieval_results(["a", "b", "c"], ["a", "c", "b"], limit=3)
    assert {item_id for item_id, _ in fused} == {"a", "b", "c"}
    assert fused[0][0] == "a"  # top of both lists -> top after fusion


# -- chunk store --------------------------------------------------------------


def test_chunk_store_loads_and_hydrates(tmp_path) -> None:
    record = {
        "chunk_id": "german-laws::gg::art-5",
        "source_id": "german-laws::gg",
        "title": "Grundgesetz",
        "text": "Jeder hat das Recht ...",
        "metadata": {
            "citation": "GG Art 5",
            "law_code": "GG",
            "source_url": "https://www.gesetze-im-internet.de/gg/",
            "hierarchy": ["I. - Die Grundrechte", "Art 5"],
        },
    }
    path = tmp_path / "chunks.jsonl"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    store = ChunkStore.from_jsonl(path)

    assert len(store) == 1
    chunk = store.get("german-laws::gg::art-5")
    assert chunk is not None
    assert chunk.citation == "GG Art 5"
    assert chunk.hierarchy == ["I. - Die Grundrechte", "Art 5"]
    assert store.hydrate(["german-laws::gg::art-5", "missing"]) == [chunk]


def test_chunk_store_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        ChunkStore.from_jsonl(tmp_path / "does-not-exist.jsonl")


# -- dense point ids ----------------------------------------------------------


def test_point_id_is_deterministic_and_unique() -> None:
    assert point_id_for("german-laws::gg::art-5") == point_id_for("german-laws::gg::art-5")
    assert point_id_for("german-laws::gg::art-5") != point_id_for("german-laws::gg::art-6")


# -- model wrappers are lazy --------------------------------------------------


def test_embedding_model_does_not_load_for_empty_input() -> None:
    model = EmbeddingModel("BAAI/bge-m3")
    assert model.encode([]) == []
    assert model._model is None  # never loaded the ~2GB weights


def test_reranker_does_not_load_for_empty_candidates() -> None:
    reranker = CrossEncoderReranker("BAAI/bge-reranker-v2-m3")
    assert reranker.rerank("query", []) == []
    assert reranker._model is None
