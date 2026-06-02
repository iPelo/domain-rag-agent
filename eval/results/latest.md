# Retrieval Evaluation

- Run: `20260602T175703Z`
- Golden set: `eval/golden_set.jsonl`
- Cases: 44
- Top-k: 5

## Summary

| Config | Completed | Hit rate | Mean precision@k | Mean MRR | Errors |
|---|---:|---:|---:|---:|---:|
| bm25 | 44/44 | 0.886 | 0.177 | 0.777 | 0 |
| dense | 44/44 | 0.977 | 0.195 | 0.883 | 0 |
| hybrid | 44/44 | 1.000 | 0.200 | 0.920 | 0 |
