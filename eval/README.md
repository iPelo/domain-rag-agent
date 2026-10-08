# Retrieval evaluation

`golden_set.jsonl` contains 44 manually selected questions with expected chunk IDs
and answer text. The evaluation checks retrieved IDs, not the answer text.

After building the corpus and Qdrant index, run:

```bash
make eval
# Also evaluate the optional reranker:
uv run python scripts/run_eval.py --include-rerank
```

The report compares BM25, dense, and hybrid search using hit rate, precision at k,
and mean reciprocal rank. Reports are written to `results/`; the repository keeps
a [saved report](results/latest.md) and its per-question [JSON results](results/latest.json).
Check completed-case counts and errors before comparing scores. These results
measure retrieval on a small set, not the correctness of generated legal answers.

To add a question, use an existing record as an example. Required fields are
`id`, `query`, `expected_answer`, and a nonempty `expected_source_chunks` list.
Chunk IDs come from the runtime JSONL file (`data/processed/chunks.curated.jsonl`).
Its records contain text, source IDs, offsets, and metadata such as law code,
citation, heading hierarchy, and source URL. Long sections can span several IDs.

`make queries` runs the separate informal examples in `example_queries.jsonl`.
`make chunking-compare` compares legal-heading, fixed, and recursive splitting on
six laws. Its lowercase-first-letter check is only a heuristic for sentence cuts.
