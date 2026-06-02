# Retrieval Evaluation

- Run: `20260602T172245Z`
- Golden set: `eval/golden_set.jsonl`
- Cases: 44
- Top-k: 5

## Summary

| Config | Completed | Hit rate | Mean precision@k | Mean MRR | Errors |
|---|---:|---:|---:|---:|---:|
| bm25 | 44/44 | 0.886 | 0.177 | 0.777 | 0 |
| dense | 0/44 | 0.000 | 0.000 | 0.000 | 1 |
| hybrid | 0/44 | 0.000 | 0.000 | 0.000 | 1 |

## dense Errors

- Qdrant unavailable: ResponseHandlingException: [Errno 61] Connection refused

## hybrid Errors

- Qdrant unavailable: ResponseHandlingException: [Errno 61] Connection refused
