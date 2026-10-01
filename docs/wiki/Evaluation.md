# Evaluation

The evaluation harness measures retrieval independently from answer generation.
This makes it easier to tell whether a bad answer started with poor search or
with the language model.

## Dataset

`eval/golden_set.jsonl` contains 44 curated questions with expected chunk IDs.
The set includes exact references, topic questions, and paraphrased questions.

## Metrics

- **Hit rate at k:** the share of questions with at least one expected chunk in
  the first k results.
- **Precision at k:** the share of returned chunks that belong to the expected
  set.
- **Mean reciprocal rank:** the average reciprocal rank of the first expected
  result. Earlier correct results receive more credit.

## Running the Evaluation

Qdrant must be running and indexed:

```bash
make up
make index
make eval
```

Reports are written to `eval/results/`. The repository keeps `latest.json` and
`latest.md` so the README can report reproducible numbers.

## Current Result

| Mode | Hit rate at 5 | MRR |
|---|---:|---:|
| BM25 | 0.886 | 0.777 |
| Dense | 0.977 | 0.883 |
| Hybrid | **1.000** | **0.920** |

## Interpretation

The current result supports using hybrid retrieval for this dataset. It does
not show that generated answers are legally correct. A larger evaluation set
and a separate answer-faithfulness test are still needed.
