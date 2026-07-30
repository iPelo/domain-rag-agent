from app.retrieval.rrf import reciprocal_rank_fusion


# Convenience wrapper: feed the dense and BM25 id lists into RRF
# and return the fused order. Kept separate from rrf.py so the
# generic fusion stays reusable and easy to test on its own.
def fuse_retrieval_results(
    dense_chunk_ids: list[str],
    bm25_chunk_ids: list[str],
    *,
    limit: int = 10,
) -> list[tuple[str, float]]:
    return reciprocal_rank_fusion([dense_chunk_ids, bm25_chunk_ids], limit=limit)
