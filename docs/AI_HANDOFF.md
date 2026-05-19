# AI Handoff

This project is `GermanLawRAG`, a RAG assistant over German federal law text.

## Current State

- Domain: German legal texts.
- Raw dataset path: `data/raw/german-laws/`.
- Dataset shape: cloned `bundestag/gesetze` Markdown repository.
- Each law normally lives at `data/raw/german-laws/<letter>/<slug>/index.md`.
- Generated processed files are local-only and ignored by Git:
  - `data/processed/documents.jsonl`
  - `data/processed/chunks.jsonl`
  - `data/processed/chunks.curated.jsonl`

## Public Repo Safety

This repository is public. Do not commit:

- `.env` or any `.env.*` file except `.env.example`
- API keys, tokens, certificates, private keys, or credentials
- `data/raw/german-laws/` or other raw datasets
- `data/processed/*.jsonl` generated corpus files
- local vector stores, database files, caches, `.DS_Store`, `.idea/`, `.claude/`, or `.venv/`

Before pushing, run:

```bash
git status --short --ignored
git check-ignore -v data/raw/german-laws/g/gg/index.md data/processed/chunks.jsonl .env
```

If a file under `data/raw/` or `data/processed/` appears as trackable, stop and fix `.gitignore` before committing.

## Ingestion

The ingestion code is source-specific for `bundestag/gesetze` Markdown:

- `backend/app/ingestion/loaders.py`
  - skips nested `.git` and dotfiles
  - only reads `index.md` inside the `german-laws` dataset
  - parses YAML-like front matter
  - stores metadata such as `law_code`, `slug`, `origslug`, `source_url`
- `backend/app/ingestion/chunking.py`
  - supports `legal-heading`, `fixed`, and `recursive` strategies
  - production default is `legal-heading`
  - creates stable chunk IDs such as `german-laws::gg::art-5`
  - stores citation metadata such as `GG Art 5`

Build chunks:

```bash
make chunks
```

The last known full build produced:

```text
6,636 documents
178,695 chunks
```

## Retrieval

New retrieval/indexing work has been added:

- `backend/app/retrieval/embeddings.py`: lazy `sentence-transformers` embedding wrapper
- `backend/app/retrieval/dense.py`: Qdrant collection, upsert, and dense search
- `backend/app/retrieval/bm25.py`: lexical BM25 search with legal-token handling
- `backend/app/retrieval/service.py`: dense/BM25/hybrid retrieval orchestration
- `backend/app/retrieval/rerank.py`: lazy cross-encoder reranking
- `backend/app/retrieval/store.py`: in-memory chunk store
- `scripts/build_index.py`: embeds chunks and upserts vectors to Qdrant
- `scripts/compare_chunking.py`: compares chunking strategies

Build the curated retrieval index:

```bash
make up
make index
```

Use `make index-all` only for the full corpus.

The local Qdrant collection should have the same point count as the runtime
chunk file line count. Check with:

```bash
wc -l data/processed/chunks.curated.jsonl
curl -s http://localhost:6333/collections/german_law_chunks
```

If Qdrant has fewer points than `chunks.curated.jsonl`, the previous build was
interrupted; rerun `make index`.

Last verified local curated index:

```text
15,174 runtime chunks
15,174 Qdrant points
```

## API

The FastAPI app now exposes:

- `GET /health`
- `GET /index/stats`
- `GET /retrieve?q=Meinungsfreiheit&law_code=GG`

## Verification

These passed after the latest cleanup:

```bash
uv run ruff check .
uv run mypy
uv run pytest
python3 -m compileall -q backend scripts
```

Also verified locally:

```bash
make index
make queries
GET /index/stats
GET /retrieve?q=§%20242%20StGB&top_k=1
```

`make queries` currently meets 8/10 loose expectations. The exact-reference
query `§ 242 StGB` is pinned correctly; the two remaining misses are broad
semantic baseline-quality issues, not setup failures.

## Next Good Step

Move into the next vertical slice:

1. Start the API with `make dev`.
2. Check `/index/stats`.
3. Try `/retrieve?q=Meinungsfreiheit&law_code=GG`.
4. Add generation with grounded citations.
5. Expand the eval set beyond the 10 smoke queries.
