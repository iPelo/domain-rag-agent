# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**GermanLawRAG** — production-grade retrieval-augmented assistant over German federal law text (`gesetze-im-internet.de` / `bundestag/gesetze` Markdown corpus). The end goal is hybrid retrieval (BM25 + dense + RRF + reranker), an agent loop with tools, and a real evaluation harness — see `README-01-rag-agent.md` for the full roadmap and `docs/decisions.md` for the rationale behind each choice.

This is a portfolio project; **the differentiator is the evaluation harness and defensible engineering decisions**, not the chat UI. When adding features, prefer changes that make trade-offs measurable (e.g. swapping chunkers, comparing retrievers) over surface polish.

## Public-repo safety (read before committing)

This repository is **public** on GitHub. Never commit:

- `.env` or any `.env.*` except `.env.example`
- API keys, tokens, certificates, private keys, or credentials
- `data/raw/german-laws/` or any other raw dataset
- `data/processed/*.jsonl` generated corpus files
- local vector stores, database files, caches, `.DS_Store`

Before pushing, sanity-check:

```bash
git status --short --ignored
git check-ignore -v data/raw/german-laws/g/gg/index.md data/processed/chunks.jsonl .env
```

If anything under `data/raw/` or `data/processed/` shows as trackable, stop and fix `.gitignore` first.

## Commands

```bash
make install        # uv sync --extra dev
make up             # docker compose up -d  (qdrant + postgres)
make down
make dev            # uvicorn app.main:app --reload --app-dir backend
make chunks         # build processed corpus from data/raw/german-laws
make test           # uv run pytest
make lint           # ruff check + mypy
make format         # ruff format + ruff --fix
```

Single-test invocation:

```bash
uv run pytest backend/tests/test_german_law_ingestion.py::test_loads_german_law_markdown_and_chunks_by_legal_heading -v
```

Quick parser smoke test (no full corpus build):

```bash
uv run python scripts/build_chunks.py --raw-dir data/raw/german-laws --limit 5
```

Type checking targets `backend/app` in strict mode; tests live under `backend/tests` with `pythonpath=["backend"]` so imports are `from app.<module> import ...`.

## Architecture

Four layers, each a backend module:

1. **`app.ingestion`** — load Markdown laws → parse YAML-ish front matter → chunk by legal heading → JSONL.
2. **`app.retrieval`** — BM25 (`rank_bm25`) + dense (Qdrant) + Reciprocal Rank Fusion + reranker stub.
3. **`app.agent`** — system prompt + `RetrievalTool` stub (not yet wired).
4. **`app.eval`** — `precision_at_k`, `mean_reciprocal_rank`; LLM-as-judge to come.

Data flow:

```
data/raw/german-laws/<letter>/<slug>/index.md
  -> app.ingestion.pipeline.build_processed_corpus
  -> data/processed/documents.jsonl + chunks.jsonl
  -> (next) embed + upsert into Qdrant collection `german_law_chunks`
  -> /retrieve endpoint
```

### Ingestion details that matter

The loader (`backend/app/ingestion/loaders.py`) is **source-specific** for `bundestag/gesetze`:

- Skips dotfiles and nested `.git`.
- Inside `german-laws/`, only reads `index.md` (one law per directory).
- Parses YAML-like front matter, preserving `jurabk` → `law_code`, `slug`, `origslug`, source URL.
- Source IDs use the form `german-laws::<slug>` (e.g. `german-laws::gg`).

The chunker (`backend/app/ingestion/chunking.py`):

- Splits by Markdown headings, falling back to fixed-size (1600 chars, 180 overlap) when a section is too long.
- Emits stable chunk IDs like `german-laws::gg::art-5` and citation strings like `GG Art 5`.
- Stores hierarchy (e.g. `["I. - Die Grundrechte", "Art 5"]`) so citations can include parent context.

If you add a new dataset, branch on `document.metadata["dataset"]` in `chunk_document` rather than rewriting the existing law-specific path.

### Last successful corpus build

```
6,636 documents
178,695 chunks
```

If a run produces wildly different numbers, the parser or the raw dataset layout has changed — investigate before overwriting `data/processed/`.

## Configuration

Settings live in `backend/app/config.py` (`pydantic-settings`), loaded from `.env`. Defaults assume local Docker services (`qdrant: http://localhost:6333`, postgres on `5432`). Embedding default is `BAAI/bge-m3`, reranker is `BAAI/bge-reranker-v2-m3`. `data_raw_dir` defaults to `data/raw` but the Makefile points the chunker at `data/raw/german-laws` explicitly.

## Current State & Next Step

Implemented: ingestion pipeline end-to-end + tests; retrieval/agent/eval modules exist as stubs.

Not yet implemented: embedding, Qdrant indexing, `/retrieve` endpoint, agent loop, evaluation runner.

Recommended next vertical slice:

1. Read `data/processed/chunks.jsonl`.
2. Embed chunk text with the configured embedding model.
3. Create (or recreate) the Qdrant collection `german_law_chunks`.
4. Upsert chunk vectors + metadata.
5. Add a `/retrieve` endpoint returning top chunks with citations.

After that: BM25 index → RRF fusion → reranker → golden set of 30–50 query/expected-source triples (the eval harness is what makes this project defensible).

## Verification status (from last handoff)

Passed:

```bash
python3 -m compileall -q backend scripts
python3 scripts/build_chunks.py --raw-dir data/raw/german-laws
```

`uv run pytest` was not run in the prior environment (no pytest in non-uv Python). Run `uv sync --extra dev` first.
