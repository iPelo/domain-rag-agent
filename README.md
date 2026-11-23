# GermanLawRAG

Hybrid search and cited, grounded answers over German federal law, with an
evaluation suite for both retrieval and answers.

```
ingest → chunk → BM25 + Qdrant → RRF → rerank → grounded answer → citation check
```

- **Ingest and chunk:** Markdown laws from [bundestag/gesetze](https://github.com/bundestag/gesetze)
  are split along their own headings (§ / Art.), so a chunk is usually one section.
  Each chunk keeps its law code, heading hierarchy, and source URL.
- **Retrieve:** BM25 (with German umlaut folding) and dense vectors in Qdrant
  (`BAAI/bge-m3`) run side by side and are merged with reciprocal rank fusion.
  Explicit references such as `§ 242 StGB` are ranked first; this boost can be
  turned off with `EXACT_REFERENCE_BOOST=false`. You can filter by law code.
- **Rerank (optional):** a cross-encoder (`BAAI/bge-reranker-v2-m3`) rescores
  the candidates.
- **Answer:** an OpenAI-compatible chat model answers only from the retrieved
  chunks and cites their IDs. Answers that cite unknown chunks, or cite nothing
  without the `[NO_ANSWER]` refusal marker, are rejected.

## Evaluation

Retrieval on the 96-question golden set (84 answerable, 12 unanswerable), top-k = 5,
curated index (30 laws, 15,174 chunks). Run `20261123T191431Z`
([full report](eval/results/latest.md)):

| Config | Hit@5 | Recall@5 | MRR@5 | nDCG@10 |
|---|---:|---:|---:|---:|
| BM25 | 0.667 | 0.593 | 0.563 | 0.553 |
| Dense | **0.845** | **0.778** | **0.720** | 0.734 |
| Hybrid (RRF) | 0.798 | 0.724 | 0.701 | 0.692 |
| Hybrid + rerank | 0.833 | 0.760 | 0.717 | **0.738** |

Only answerable questions are scored; the unanswerable ones are scored by the
answer eval. nDCG@10 per question category:

| Category | Questions | BM25 | Dense | Hybrid | Hybrid + rerank |
|---|---:|---:|---:|---:|---:|
| Original | 44 | 0.812 | 0.913 | 0.941 | 0.928 |
| Colloquial | 21 | 0.069 | 0.401 | 0.256 | 0.443 |
| Multi-section | 19 | 0.486 | 0.687 | 0.599 | 0.627 |

What this shows:

- **The original 44 questions were saturated.** Hybrid reached Hit@5 = 1.000 on
  them, which hid the real weaknesses. They mostly reuse the statute's own wording,
  so BM25 does well and RRF has two good lists to merge.
- **Hybrid is not the best mode on the harder set.** On colloquial questions BM25
  barely finds anything (nDCG@10 0.069), and equal-weight RRF lets those weak BM25
  ranks pull dense results down. Dense alone beats plain hybrid in every new category.
- **The reranker recovers most of the gap** and is roughly on par with dense
  (nDCG@10 0.738 vs 0.734, but MRR@5 0.717 vs 0.720), at the cost of a
  cross-encoder pass per query.
- **The exact-reference boost makes no measurable difference here.** No golden
  question cites a specific section (`§ 242 StGB`), so the boost is barely
  triggered: turning it off changes no BM25, dense or rerank metric and lowers
  hybrid nDCG@10 from 0.692 to 0.688. The eval cannot say whether the boost helps.

Next steps, to be validated on a held-out question set rather than tuned on
this one:

- Weighted RRF (or a dense-leaning weight) so a weak BM25 list counts for less.
- Reranking by default, after measuring its latency.
- Questions with explicit section references, so the boost is actually tested.

<!-- TODO: after `make answer-eval JUDGE=1`, add abstention accuracy, claim citation
     coverage, and the mean judge score. -->

See [eval/README.md](eval/README.md) for the metrics, categories, and answer eval.

## Screenshot

<!-- TODO: save a screenshot of the console as docs/screenshot.png and replace this
     comment with: ![GermanLawRAG console](docs/screenshot.png) -->

## Setup

You need Python 3.12, uv, Docker Compose, and Node.js 20 or newer.
From the repository root:

```bash
uv sync --extra dev --locked
npm ci --prefix frontend
cp .env.example .env
git clone --depth 1 https://github.com/bundestag/gesetze.git data/raw/german-laws
make chunks
make up
make index
```

The first index build downloads the embedding model. By default it indexes 30
selected laws; `make index-all` includes the full corpus. Both rebuild the index.

Start the backend and frontend in separate terminals:

```bash
make dev
```

```bash
npm run dev --prefix frontend
```

Open `http://localhost:5173`. The API documentation is at `http://localhost:8000/docs`.
For answers, configure `MODEL_NAME`, `MODEL_BASE_URL`, and `MODEL_API_KEY` in `.env`
with an OpenAI-compatible chat endpoint. Search works without a chat model.

| Command | What it does |
|---|---|
| `make verify` | Tests, Ruff, mypy, and the frontend build |
| `make eval` | Retrieval eval, with the boost on and off |
| `make answer-eval` | Answer eval; add `JUDGE=1` for the LLM judge |

Python, FastAPI, sentence-transformers, Qdrant, and rank-bm25 power the backend;
React, TypeScript, and Vite power the frontend.

This is a learning project, not a legal advice service. Citation checks confirm
that cited chunks were retrieved; they do not prove that every claim is correct.
