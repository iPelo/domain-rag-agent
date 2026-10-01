# GermanLawRAG Wiki

GermanLawRAG is a retrieval-augmented generation project for German federal law.
The system turns a Markdown law corpus into searchable chunks, combines lexical
and semantic retrieval, and returns source passages that can support a cited
answer.

## Wiki Pages

- [Getting Started](Getting-Started)
- [Architecture](Architecture)
- [API Reference](API-Reference)
- [Evaluation](Evaluation)
- [Design Decisions](Design-Decisions)
- [Troubleshooting](Troubleshooting)

## Project Status

The ingestion, indexing, retrieval, answer, frontend, and evaluation paths are
implemented. The project is intended for local development and portfolio use;
it is not a production legal service.

## Current Retrieval Results

| Mode | Hit rate at 5 | MRR |
|---|---:|---:|
| BM25 | 0.886 | 0.777 |
| Dense | 0.977 | 0.883 |
| Hybrid | **1.000** | **0.920** |

The golden set contains 44 curated questions. These numbers measure whether the
expected source appears in the retrieved results, not whether a generated legal
answer is correct.
