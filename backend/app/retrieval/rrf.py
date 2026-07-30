# Reciprocal Rank Fusion — merges several ranked lists into one by RANK,
# not score. Each item earns 1/(k+rank) from every list it appears in,
# and the sums are re-sorted. Items ranked highly by multiple retrievers
# rise to the top; `k` (60) softens the influence of any single list's
# exact positions. This is how dense + BM25 get combined.
def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
    limit: int = 10,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked_ids in ranked_lists:
        for rank, item_id in enumerate(ranked_ids, start=1):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
