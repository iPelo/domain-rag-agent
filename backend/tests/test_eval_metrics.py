import math

import pytest
from app.evaluation.metrics import (
    hit_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

RETRIEVED = ["a", "b", "c", "d", "e", "f"]


def test_hit_and_precision_use_only_top_k() -> None:
    assert hit_at_k(RETRIEVED, {"c"}, k=3)
    assert not hit_at_k(RETRIEVED, {"f"}, k=5)
    assert precision_at_k(RETRIEVED, {"a", "c", "f"}, k=5) == pytest.approx(2 / 5)


def test_recall_counts_share_of_expected_chunks_found() -> None:
    assert recall_at_k(RETRIEVED, {"a", "e", "z"}, k=5) == pytest.approx(2 / 3)
    assert recall_at_k(RETRIEVED, {"f"}, k=5) == 0.0


def test_reciprocal_rank_is_cut_at_k() -> None:
    assert reciprocal_rank(RETRIEVED, {"b"}, k=5) == pytest.approx(0.5)
    assert reciprocal_rank(RETRIEVED, {"f"}, k=5) == 0.0


def test_ndcg_is_one_for_ideal_ranking() -> None:
    assert ndcg_at_k(RETRIEVED, {"a", "b"}, k=10) == pytest.approx(1.0)


def test_ndcg_discounts_lower_ranks() -> None:
    expected = 1 / math.log2(3)  # one relevant chunk at rank 2
    assert ndcg_at_k(RETRIEVED, {"b"}, k=10) == pytest.approx(expected)
    assert ndcg_at_k(RETRIEVED, {"z"}, k=10) == 0.0


def test_metrics_reject_non_positive_k() -> None:
    with pytest.raises(ValueError):
        recall_at_k(RETRIEVED, {"a"}, k=0)
