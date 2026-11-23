# Retrieval Evaluation

- Run: `20261123T191431Z`
- Golden set: `eval/golden_set.jsonl`
- Cases: 96 (84 answerable, 12 unanswerable; only answerable cases are scored)
- Top-k: 5
- Index: curated (30 laws, 15,174 chunks; scope manifest)

## Summary

| Config | Boost | Completed | Hit@k | Precision@k | Recall@k | MRR@k | nDCG@10 | Errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | on | 84/84 | 0.667 | 0.143 | 0.593 | 0.563 | 0.553 | 0 |
| dense | on | 84/84 | 0.845 | 0.190 | 0.778 | 0.720 | 0.734 | 0 |
| hybrid | on | 84/84 | 0.798 | 0.171 | 0.724 | 0.701 | 0.692 | 0 |
| hybrid_rerank | on | 84/84 | 0.833 | 0.183 | 0.760 | 0.717 | 0.738 | 0 |
| bm25_no_boost | off | 84/84 | 0.667 | 0.143 | 0.593 | 0.563 | 0.553 | 0 |
| dense_no_boost | off | 84/84 | 0.845 | 0.190 | 0.778 | 0.720 | 0.734 | 0 |
| hybrid_no_boost | off | 84/84 | 0.798 | 0.171 | 0.724 | 0.695 | 0.688 | 0 |
| hybrid_rerank_no_boost | off | 84/84 | 0.833 | 0.183 | 0.760 | 0.717 | 0.738 | 0 |
