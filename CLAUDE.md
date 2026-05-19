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
- local vector stores, database files, caches, `.DS_Store`, `.idea/`, `.claude/`, `.venv/`

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
make index          # build curated Qdrant index
make index-all      # build full Qdrant index
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
2. **`app.retrieval`** — BM25 (`rank_bm25`) + dense (Qdrant) + Reciprocal Rank Fusion + optional cross-encoder reranker.
3. **`app.agent`** — system prompt + `RetrievalTool` stub (not yet wired).
4. **`app.eval`** — `precision_at_k`, `mean_reciprocal_rank`; LLM-as-judge to come.

Data flow:

```
data/raw/german-laws/<letter>/<slug>/index.md
  -> app.ingestion.pipeline.build_processed_corpus
  -> data/processed/documents.jsonl + chunks.jsonl
  -> scripts/build_index.py
  -> data/processed/chunks.curated.jsonl + Qdrant collection `german_law_chunks`
  -> /retrieve endpoint
```

### Ingestion details that matter

The loader (`backend/app/ingestion/loaders.py`) is **source-specific** for `bundestag/gesetze`:

- Skips dotfiles and nested `.git`.
- Inside `german-laws/`, only reads `index.md` (one law per directory).
- Parses YAML-like front matter, preserving `jurabk` → `law_code`, `slug`, `origslug`, source URL.
- Source IDs use the form `german-laws::<slug>` (e.g. `german-laws::gg`).

The chunker (`backend/app/ingestion/chunking.py`):

- Supports `legal-heading`, `fixed`, and `recursive` strategies.
- Production default is `legal-heading`.
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

Settings live in `backend/app/config.py` (`pydantic-settings`), loaded from `.env`. Defaults assume local Docker services (`qdrant: http://localhost:6333`, postgres on `5432`). Embedding default is `BAAI/bge-m3`, reranker is `BAAI/bge-reranker-v2-m3`. `data_raw_dir` defaults to `data/raw/german-laws`, and `index_chunks_path` defaults to `data/processed/chunks.curated.jsonl`.

## Current State & Next Step

Implemented:

- ingestion pipeline end-to-end + tests
- curated corpus selection
- Qdrant indexing script
- BM25 retrieval
- dense retrieval
- hybrid RRF retrieval
- optional reranker
- `/index/stats` and `/retrieve` endpoints

Not yet implemented:

- agent loop
- generation with cited answers
- evaluation runner and golden set

Recommended next vertical slice:

1. Start the API with `make dev`.
2. Check `/index/stats`.
3. Try `/retrieve?q=Meinungsfreiheit&law_code=GG`.
4. Add generation with grounded citations.
5. Wire generation into the agent retrieve tool.

The Qdrant point count must match `wc -l data/processed/chunks.curated.jsonl`.
If it is lower, a previous index build was interrupted; rerun `make index`.

After that: generation with citations → agent retrieve tool → golden set of 30–50 query/expected-source triples.

## Verification status (from last handoff)

Passed:

```bash
python3 -m compileall -q backend scripts
python3 scripts/build_chunks.py --raw-dir data/raw/german-laws
uv run ruff check .
uv run mypy
uv run pytest
```

Also verified:

```bash
make index
make queries
GET /index/stats
GET /retrieve?q=§%20242%20StGB&top_k=1
```

Latest local curated index count: 15,174 runtime chunks and 15,174 Qdrant
points. `make queries` currently meets 8/10 loose smoke expectations; the
remaining misses are broad semantic baseline-quality issues.
