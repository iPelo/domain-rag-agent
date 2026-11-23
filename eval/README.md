# Retrieval evaluation

`golden_set.jsonl` contains 96 manually written questions with expected chunk IDs
and answer text. The evaluation checks retrieved IDs, not the answer text.

| Category | Cases | What it tests |
|---|---:|---|
| original (no `category` field) | 44 | Direct questions, mostly one section each |
| `colloquial` | 21 | Everyday wording with few legal terms ("Mein Vermieter will mir kündigen...") |
| `multi_section` | 19 | Answers that need 2-3 sections, e.g. Mord vs. Totschlag (§§ 211, 212 StGB) |
| `unanswerable` | 12 | State law, foreign law, or non-legal questions; `expected_source_chunks` is empty |

Every expected chunk ID was checked against the curated 30-law chunk file built
from the `bundestag/gesetze` snapshot, and expected answers follow that snapshot's
text. Newer versions of a law may differ.

After building the corpus and Qdrant index, run:

```bash
make eval
# Also evaluate the optional reranker:
uv run python scripts/run_eval.py --include-rerank
```

The report compares BM25, dense, and hybrid search using hit@k, precision@k,
recall@k, MRR@k (default k=5), and nDCG@10. Every metric is averaged over all
answerable cases, and a case that fails counts as 0. Most questions have one
relevant chunk, so precision@5 tops out at 0.2 for them; recall@k and nDCG@10 are
more informative for questions that span several sections. Unanswerable
questions (`expected_source_chunks: []`) are counted but not scored, since ranking
metrics are undefined without relevant chunks. Each mode runs twice: with the exact-reference boost
(chunks matching a law code and section named in the query, such as `§ 242 StGB`,
are ranked first) and without it (`*_no_boost`). Use `--boost on` or `--boost off`
to run only one. The API uses the `EXACT_REFERENCE_BOOST` setting. Reports are written to `results/`; the repository keeps
a [saved report](results/latest.md) and its per-question [JSON results](results/latest.json).
Check completed-case counts and errors before comparing scores. These results
measure retrieval on a small set, not the correctness of generated legal answers.

To add a question, use an existing record as an example. Required fields are
`id`, `query`, `expected_answer`, and an `expected_source_chunks` list (empty
for questions the corpus cannot answer).
Chunk IDs come from the runtime JSONL file (`data/processed/chunks.curated.jsonl`).
Its records contain text, source IDs, offsets, and metadata such as law code,
citation, heading hierarchy, and source URL. Long sections can span several IDs.

`make queries` runs the separate informal examples in `example_queries.jsonl`.
`make chunking-compare` compares legal-heading, fixed, and recursive splitting on
six laws. Its lowercase-first-letter check is only a heuristic for sentence cuts.

## Answer evaluation

`answer_set.jsonl` has 20 cases taken from the golden set: 14 answerable and 6
unanswerable. `make answer-eval` generates an answer for each one with the
configured `MODEL_*` endpoint and checks:

- **Abstention:** answerable questions get an answer, and unanswerable ones get
  `no_answer`. Answers rejected by the service's citation check count as wrong.
- **Claim citations:** the answer is split into sentences and list items (a
  heuristic that keeps abbreviations such as `Abs.` and `Nr.` together). Every
  claim must cite a retrieved chunk ID, and no unknown IDs may appear.
- **Expected sources:** whether at least one expected chunk was cited.
- **Faithfulness (optional):** `make answer-eval JUDGE=1` asks an LLM judge to
  score each answered case from 1 to 5 against `expected_answer` and the cited
  source text. Set `JUDGE_MODEL_*` to use a different model than the one being
  evaluated. Judge scores are only a rough signal, not a legal review.

Reports are written to `results/answer_eval_<run>.md` and `results/answer_latest.*`.
