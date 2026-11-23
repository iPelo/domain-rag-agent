import json

from app.retrieval.index_info import (
    CURATED_LAW_SLUGS,
    describe_index,
    infer_scope,
    write_manifest,
)


def _write_chunks(path, slugs):
    lines = [
        json.dumps({"chunk_id": f"german-laws::{slug}::x", "metadata": {"slug": slug}})
        for slug in slugs
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_infer_scope() -> None:
    assert infer_scope(set(CURATED_LAW_SLUGS)) == "curated"
    assert infer_scope({"gg", "bgb"}) == "curated (partial)"
    assert infer_scope({*CURATED_LAW_SLUGS, "tierschg"}) == "all"


def test_describe_index_infers_scope_without_manifest(tmp_path) -> None:
    path = tmp_path / "chunks.curated.jsonl"
    _write_chunks(path, ["gg", "gg", "bgb"])

    info = describe_index(path)

    assert info["chunk_count"] == 3
    assert info["law_count"] == 2
    assert info["scope"] == "curated (partial)"
    assert info["scope_source"] == "inferred from law slugs"


def test_describe_index_prefers_manifest(tmp_path) -> None:
    path = tmp_path / "chunks.curated.jsonl"
    _write_chunks(path, ["gg"])
    write_manifest(path, {"scope": "all", "limit": 1})

    info = describe_index(path)

    assert info["scope"] == "all"
    assert info["scope_source"] == "manifest"
    assert info["manifest"]["limit"] == 1
