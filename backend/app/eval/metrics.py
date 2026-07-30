# Retrieval-quality metrics used by the eval harness (scripts/run_eval.py).
# precision_at_k = of the top-k results, what fraction are in the expected set.
def precision_at_k(retrieved_ids: list[str], expected_ids: set[str], *, k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    if not expected_ids:
        return 0.0

    top_k = retrieved_ids[:k]
    hits = sum(1 for item_id in top_k if item_id in expected_ids)
    return hits / k


# MRR = 1/rank of the FIRST correct hit (1.0 if the top
# result is right, 0.5 if second...), so it rewards putting a
# relevant chunk as high as possible. 0 if none are relevant.
def mean_reciprocal_rank(retrieved_ids: list[str], expected_ids: set[str]) -> float:
    if not expected_ids:
        return 0.0

    for index, item_id in enumerate(retrieved_ids, start=1):
        if item_id in expected_ids:
            return 1.0 / index
    return 0.0
