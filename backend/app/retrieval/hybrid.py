from app.retrieval.rrf import reciprocal_rank_fusion


def fuse_retrieval_results(
    dense_chunk_ids: list[str],
    bm25_chunk_ids: list[str],
    *,
    limit: int = 10,
) -> list[tuple[str, float]]:
    return reciprocal_rank_fusion([dense_chunk_ids, bm25_chunk_ids], limit=limit)
