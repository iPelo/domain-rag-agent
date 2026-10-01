# GermanLawRAG

[![CI](https://github.com/iPelo/domain-rag-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/iPelo/domain-rag-agent/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

GermanLawRAG is a retrieval-augmented generation project for German federal law.
It parses legal texts, retrieves relevant sections with hybrid search, and can
generate answers that cite the source chunks used.

> This is a portfolio project, not a legal advice service.

## Features

- Legal-heading chunking for articles and sections such as `Art 5` and `§ 433`
- BM25 keyword search and dense vector search
- Reciprocal rank fusion for hybrid retrieval
- Optional cross-encoder reranking
- Citation validation for generated answers
- FastAPI backend and React/TypeScript frontend
- Reproducible retrieval evaluation and CI checks

## Results

The current golden set contains 44 questions evaluated at `k=5`.

| Mode | Hit rate | MRR |
|---|---:|---:|
| BM25 | 0.886 | 0.777 |
| Dense | 0.977 | 0.883 |
| Hybrid | **1.000** | **0.920** |

These results measure retrieval on a small curated dataset, not legal answer
accuracy. See [the latest report](eval/results/latest.md) for details.

## Architecture

```text
Markdown laws
    -> metadata parsing and legal-heading chunking
    -> processed JSONL
    -> BM25 + Qdrant vector search
    -> reciprocal rank fusion
    -> optional reranking
    -> cited passages
    -> optional generated answer
```

| Layer | Technology |
|---|---|
| API | Python, FastAPI, Pydantic |
| Retrieval | rank-bm25, sentence-transformers, Qdrant |
| Models | BAAI/bge-m3, optional BAAI/bge-reranker-v2-m3 |
| Frontend | React, TypeScript, Vite |
| Quality | pytest, Ruff, mypy, GitHub Actions |

## Quick Start

Requirements: Python 3.12, `uv`, Docker Compose, and Node.js 18 or newer.

```bash
git clone https://github.com/iPelo/domain-rag-agent.git
cd domain-rag-agent
uv sync --extra dev
npm ci --prefix frontend
cp .env.example .env

git clone --depth 1 https://github.com/bundestag/gesetze.git \
  data/raw/german-laws
make chunks
make up
make index
```

Start the API and frontend in separate terminals:

```bash
make dev
npm run dev --prefix frontend
```

- Frontend: `http://localhost:5173`
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Example Request

```bash
curl --get http://localhost:8000/retrieve \
  --data-urlencode "q=Wo ist die Meinungsfreiheit geregelt?" \
  --data-urlencode "mode=hybrid" \
  --data-urlencode "top_k=5" \
  --data-urlencode "law_code=GG"
```

The `/answer` endpoint also requires an OpenAI-compatible model endpoint. Set
`MODEL_NAME`, `MODEL_BASE_URL`, and `MODEL_API_KEY` in `.env` to enable it.
Retrieval works without a chat model.

## Development

```bash
make verify   # tests, lint, type checks, and frontend build
make eval     # retrieval evaluation; requires a running indexed Qdrant
```

## Documentation

The [project wiki](https://github.com/iPelo/domain-rag-agent/wiki) covers setup,
architecture, API endpoints, evaluation, design decisions, and troubleshooting.
The wiki source is also kept in [`docs/wiki`](docs/wiki).

## Limitations

- The evaluation set is small and manually curated.
- Generated answers do not yet have a separate faithfulness benchmark.
- Citation validation checks chunk IDs, not every individual claim.
- The Markdown parser depends on the structure of the source conversion.
- Authentication, rate limiting, monitoring, and index versioning are not implemented.

## License

The project is available under the [MIT License](LICENSE). The source law corpus
is maintained separately and is not included in this repository.
