def precision_at_k(retrieved_ids: list[str], expected_ids: set[str], *, k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    if not expected_ids:
        return 0.0

    top_k = retrieved_ids[:k]
    hits = sum(1 for item_id in top_k if item_id in expected_ids)
    return hits / k


def mean_reciprocal_rank(retrieved_ids: list[str], expected_ids: set[str]) -> float:
    if not expected_ids:
        return 0.0

    for index, item_id in enumerate(retrieved_ids, start=1):
        if item_id in expected_ids:
            return 1.0 / index
    return 0.0
