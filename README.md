# GermanLawRAG

A search app for German federal law texts. It finds relevant passages and can
use them to generate short answers with source citations.

## Features

- Search by keywords (BM25), meaning (dense search), or a combination of both.
- Filter results by law code, such as `GG` or `BGB`.
- Optionally rerank passages before returning results.
- Generate answers with citations to the retrieved passages.
- Compare search methods using 44 manually selected questions.

## Technologies

Python, FastAPI, sentence-transformers, Qdrant, and rank-bm25 for the backend;
React, TypeScript, and Vite for the frontend.

## Getting Started

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

Run `make verify` for checks or `make eval` for the [retrieval evaluation](eval/README.md).
This is a learning project, not a legal advice service. Citation checks validate
source IDs, not whether every generated claim is correct.
