# GermanLawRAG

GermanLawRAG is a retrieval service for German federal law texts. It ingests the
local `bundestag/gesetze` Markdown corpus, builds searchable chunks, and returns
answers with citations back to the source passages.

The scope is intentionally narrow:

- Dataset/domain: GermanLawRAG
- Primary source family: Gesetze im Internet / Bundestag `gesetze` Markdown data
- First implementation target: ingest law documents, retrieve cited passages, and answer with source-grounded citations

## Current Status

The backend can parse the local law corpus, build a curated Qdrant index, run
BM25 and dense retrieval, fuse rankings, rerank results, and produce cited
answers from retrieved chunks.

## Architecture

```text
[ Raw Bundestag/Gesetze Markdown data ]
        |
        v
[ Ingestion: parse -> normalize -> chunk ]
        |
        v
[ Qdrant vector store ] + [ BM25 index ]
        |
        v
[ FastAPI backend ]
        |-- dense retrieval
        |-- BM25 retrieval
        |-- hybrid fusion
        |-- reranking
        |-- cited answer workflow
        |-- evaluation harness
        |
        v
[ React + Vite frontend ]
```

## Repository Layout

```text
germanlawrag/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── workflow/
│   │   └── eval/
│   └── tests/
├── data/
│   ├── raw/
│   └── processed/
├── docs/
│   ├── architecture.md
│   ├── data-sources.md
│   └── decisions.md
├── eval/
│   ├── golden_set.example.jsonl
│   └── results/
├── frontend/
├── scripts/
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Local Development

1. Create your environment:

```bash
uv sync --extra dev
```

2. Copy environment variables:

```bash
cp .env.example .env
```

3. Start local services:

```bash
docker compose up -d
```

4. Run the backend:

```bash
uv run uvicorn app.main:app --reload --app-dir backend
```

5. Open:

```text
http://localhost:8000/health
```

6. Build processed documents and chunks from the added dataset:

```bash
make chunks
```

This writes:

```text
data/processed/documents.jsonl
data/processed/chunks.jsonl
```

For a quick parser check:

```bash
uv run python scripts/build_chunks.py --raw-dir data/raw/german-laws --limit 5
```

7. Build the first Qdrant retrieval index:

```bash
make up
make index
```

`make index` embeds the curated subset of major German codes for development.
Use `make index-all` only when you want to embed the full corpus.

8. Configure cited answers:

```bash
MODEL_PROVIDER=hosted
MODEL_NAME=<model-name>
MODEL_BASE_URL=<chat-completions-base-url>
MODEL_API_KEY=<your-key>
```

Then call:

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"Wo ist die Meinungsfreiheit geregelt?","top_k":5}'
```

The model settings are optional. Retrieval works without them, while `/answer`
returns a clear `503` until they are configured.

## Verification

Run every local check with one command:

```bash
make verify
```

This runs the backend tests, Ruff, mypy, TypeScript checks, and the frontend
production build.

## VS Code

This repo includes `.vscode/` settings for Python, Ruff, pytest, and a FastAPI launch configuration.

Recommended workflow:

1. Open the repository folder in VS Code.
2. Install recommended extensions when prompted.
3. Select `.venv/bin/python` as the interpreter after running `uv sync`.
4. Use the "FastAPI: backend" launch configuration.

Useful tasks:

- `GermanLawRAG: Build Retrieval Index`: starts Qdrant and rebuilds the curated index.
- `GermanLawRAG: Run Retrieval Evaluation`: runs the golden-set retrieval report.

## Current Evaluation

The golden set contains 44 questions. The latest recorded top-5 retrieval
results are:

| Mode | Hit rate | Mean MRR |
|---|---:|---:|
| BM25 | 0.886 | 0.777 |
| Dense | 0.977 | 0.883 |
| Hybrid | 1.000 | 0.920 |

The next meaningful improvement is answer-quality evaluation with a configured
chat model. Retrieval evaluation and the main application flow are implemented.
