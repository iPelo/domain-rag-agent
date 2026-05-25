# GermanLawRAG

Production-grade retrieval-augmented assistant for German legal texts.

The project is built around one focused domain:

- Dataset/domain: GermanLawRAG
- Primary source family: Gesetze im Internet / Bundestag `gesetze` Markdown data
- First implementation target: ingest law documents, retrieve cited passages, and answer with source-grounded citations

## Current Status

Project structure is ready and the ingestion pipeline understands the local `data/raw/german-laws` clone.

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
        |-- agent tools
        |-- evaluation harness
        |
        v
[ Next.js frontend ]
```

## Repository Layout

```text
domain-rag-agent/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── agent/
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

## VS Code

This repo includes `.vscode/` settings for Python, Ruff, pytest, and a FastAPI launch configuration.

Recommended workflow:

1. Open the repository folder in VS Code.
2. Install recommended extensions when prompted.
3. Select `.venv/bin/python` as the interpreter after running `uv sync`.
4. Use the "FastAPI: backend" launch configuration.

## Next Milestones

1. Keep the cloned `german-laws` data at `data/raw/german-laws/`.
2. Build normalized documents and legal-heading chunks.
3. Add embeddings for `data/processed/chunks.jsonl`.
4. Store embedded chunks in Qdrant.
5. Build the first 10 hand-written evaluation queries.
