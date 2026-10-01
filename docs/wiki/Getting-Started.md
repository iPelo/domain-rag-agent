# Getting Started

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Docker with Compose
- Node.js 18 or newer

## Installation

```bash
git clone https://github.com/iPelo/domain-rag-agent.git
cd domain-rag-agent
uv sync --extra dev
npm ci --prefix frontend
cp .env.example .env
```

## Corpus

The corpus is not committed to this repository. Clone it into the expected
local directory, then build the processed files:

```bash
git clone --depth 1 https://github.com/bundestag/gesetze.git \
  data/raw/german-laws
make chunks
```

The ingestion step writes `documents.jsonl` and `chunks.jsonl` under
`data/processed/`.

## Indexing

```bash
make up
make index
```

`make index` uses a curated group of major German codes. Use `make index-all`
to index the full processed corpus.

## Running the Application

Start the API:

```bash
make dev
```

Start the frontend in another terminal:

```bash
npm run dev --prefix frontend
```

The frontend runs at `http://localhost:5173` and proxies API requests to
`http://localhost:8000`.

## Answer Generation

Retrieval does not require a chat model. To use `POST /answer`, configure an
OpenAI-compatible endpoint in `.env`:

```dotenv
MODEL_PROVIDER=hosted
MODEL_NAME=your-model-name
MODEL_BASE_URL=https://your-provider.example/v1
MODEL_API_KEY=your-secret-key
```

## Verification

```bash
make verify
```

This runs backend tests, Ruff, mypy, the TypeScript compiler, and the frontend
production build.
