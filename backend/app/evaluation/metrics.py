"""Ranking metrics with binary relevance.

`expected` is the set of relevant chunk IDs for one question; `retrieved` is the
ranked list returned by the retriever. Cases with no relevant chunks
(unanswerable questions) are not scored by these functions.
"""

from __future__ import annotations

import math
from collections.abc import Sequence, Set


def hit_at_k(retrieved: Sequence[str], expected: Set[str], *, k: int) -> bool:
    _check_k(k)
    return any(item in expected for item in retrieved[:k])


def precision_at_k(retrieved: Sequence[str], expected: Set[str], *, k: int) -> float:
    """Relevant results in the top k, divided by k.

    With one relevant chunk per question the maximum is 1/k (0.2 at k=5).
    """
    _check_k(k)
    if not expected:
        return 0.0
    return sum(1 for item in retrieved[:k] if item in expected) / k


def recall_at_k(retrieved: Sequence[str], expected: Set[str], *, k: int) -> float:
    """Share of the relevant chunks that appear in the top k."""
    _check_k(k)
    if not expected:
        return 0.0
    return sum(1 for item in set(retrieved[:k]) if item in expected) / len(expected)


def reciprocal_rank(retrieved: Sequence[str], expected: Set[str], *, k: int) -> float:
    """1 / rank of the first relevant result within the top k, else 0."""
    _check_k(k)
    for rank, item in enumerate(retrieved[:k], start=1):
        if item in expected:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], expected: Set[str], *, k: int) -> float:
    """Normalized discounted cumulative gain with binary relevance."""
    _check_k(k)
    if not expected:
        return 0.0
    seen: set[str] = set()
    dcg = 0.0
    for rank, item in enumerate(retrieved[:k], start=1):
        if item in expected and item not in seen:
            seen.add(item)
            dcg += 1.0 / math.log2(rank + 1)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(len(expected), k) + 1))
    return dcg / ideal


def _check_k(k: int) -> None:
    if k <= 0:
        raise ValueError("k must be positive")
