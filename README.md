# GermanLawRAG

[![CI](https://github.com/iPelo/domain-rag-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/iPelo/domain-rag-agent/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

GermanLawRAG is a portfolio project that explores retrieval-augmented generation
for German federal law. It turns a Markdown law corpus into searchable legal
sections, combines keyword and semantic search, and can generate answers that
cite the retrieved source passages.

I built this project to learn the parts of RAG that happen before the final model
call: document parsing, chunking, hybrid retrieval, evaluation, API design, and
failure handling.

> This is a learning project, not a legal advice service. It is designed for
> local development and has not been hardened for production use.

## What It Does

- Parses the [`bundestag/gesetze`](https://github.com/bundestag/gesetze) Markdown
  corpus and preserves law metadata.
- Chunks laws around legal headings such as `Art 5` and `§ 433`, with an
  overlapping fallback for long sections.
- Supports BM25 keyword search, dense vector search, and hybrid retrieval.
- Combines BM25 and dense rankings with reciprocal rank fusion.
- Optionally reranks candidates with a cross-encoder.
- Exposes `/retrieve`, `/answer`, `/index/stats`, and `/health` through FastAPI.
- Validates generated chunk citations before returning an answer.
- Includes a React and TypeScript console for trying queries in the browser.

## Results

The checked-in golden set contains 44 retrieval questions. These are the latest
top-five results:

| Retrieval mode | Hit rate | Mean reciprocal rank |
|---|---:|---:|
| BM25 | 0.886 | 0.777 |
| Dense | 0.977 | 0.883 |
| Hybrid | **1.000** | **0.920** |

The result means hybrid search found at least one expected source in the first
five results for all 44 questions. It does **not** mean the system gives perfect
legal answers. The evaluation set is small and curated, and generated-answer
quality still needs a separate faithfulness evaluation.

Full details are in [`eval/results/latest.md`](eval/results/latest.md).

## How It Works

```text
German law Markdown
        |
        v
parse metadata -> split by legal heading -> processed JSONL
        |                                      |
        |                                      +-> BM25 index
        v
embed chunks -> Qdrant vector index            |
        |                                      |
        +------------------+-------------------+
                           v
                 reciprocal rank fusion
                           |
                    optional reranking
                           |
             retrieved passages with citations
                           |
                 optional answer generation
```

BM25 is useful for exact law names, abbreviations, and section numbers. Dense
retrieval is useful when the question paraphrases the source. Reciprocal rank
fusion combines their rank positions without pretending their raw scores are on
the same scale.

More detail: [`docs/architecture.md`](docs/architecture.md) and
[`docs/decisions.md`](docs/decisions.md).

## Tech Stack

| Area | Tools |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic |
| Retrieval | rank-bm25, sentence-transformers, Qdrant |
| Models | BAAI/bge-m3, optional BAAI/bge-reranker-v2-m3 |
| Frontend | React, TypeScript, Vite |
| Quality | pytest, Ruff, mypy, GitHub Actions |
| Local infrastructure | Docker Compose |

## Quick Start

### Requirements

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/)
- Docker Desktop or Docker Engine with Compose
- Node.js 18 or newer

### 1. Install the project

```bash
git clone https://github.com/iPelo/domain-rag-agent.git
cd domain-rag-agent
uv sync --extra dev
cp .env.example .env
npm ci --prefix frontend
```

### 2. Download and process the corpus

Raw and processed data are intentionally excluded from Git.

```bash
git clone --depth 1 https://github.com/bundestag/gesetze.git data/raw/german-laws
make chunks
```

For a smaller parser check, use:

```bash
uv run python scripts/build_chunks.py \
  --raw-dir data/raw/german-laws \
  --limit 5 \
  --documents-output data/processed/documents.sample.jsonl \
  --chunks-output data/processed/chunks.sample.jsonl
```

### 3. Build the retrieval index

```bash
make up
make index
```

`make index` builds the smaller curated index used for development. `make
index-all` indexes the full corpus and takes considerably longer.

### 4. Start the application

Run the backend:

```bash
make dev
```

In a second terminal, run the frontend:

```bash
npm run dev --prefix frontend
```

Open `http://localhost:5173`. API documentation is available at
`http://localhost:8000/docs`.

## Answer Generation

Retrieval works without a chat model. To enable `/answer`, add an OpenAI-style
chat-completions endpoint to `.env`:

```dotenv
MODEL_PROVIDER=hosted
MODEL_NAME=your-model-name
MODEL_BASE_URL=https://your-provider.example/v1
MODEL_API_KEY=your-secret-key
```

Without these values, `/answer` returns a clear `503` response while
`/retrieve` remains available.

## API Examples

Retrieve source passages:

```bash
curl --get http://localhost:8000/retrieve \
  --data-urlencode "q=Wo ist die Meinungsfreiheit geregelt?" \
  --data-urlencode "mode=hybrid" \
  --data-urlencode "top_k=5" \
  --data-urlencode "law_code=GG"
```

Generate a cited answer after configuring a model:

```bash
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"query":"Wo ist die Meinungsfreiheit geregelt?","top_k":5}'
```

## Tests and Evaluation

Run all local checks:

```bash
make verify
```

This runs the Python tests, Ruff, strict mypy checks, TypeScript checks, and the
frontend production build. GitHub Actions runs the same checks on pushes and
pull requests.

Run the retrieval evaluation after Qdrant is indexed:

```bash
make eval
```

## Project Structure

```text
backend/app/          FastAPI application and RAG modules
backend/tests/        Unit and API tests
frontend/src/         React developer console
scripts/              Ingestion, indexing, and evaluation commands
data/                 Local raw and processed data, ignored by Git
eval/                 Golden questions and latest evaluation report
docs/                 Architecture, decisions, and data notes
```

## Current Limitations

- The golden set has only 44 curated questions.
- Retrieval has been evaluated more thoroughly than generated answers.
- Citation validation checks that cited chunk IDs were retrieved; it does not
  prove that every generated statement is supported by those chunks.
- The parser depends on the structure of the Markdown conversion rather than
  the richer upstream XML.
- Authentication, rate limiting, monitoring, and index versioning are not yet
  implemented.
- The default development index covers a curated subset of the full corpus.

## What I Learned

- Domain-aware chunking can matter more than adding another model.
- BM25 and dense retrieval fail in different ways, so evaluating them
  separately makes debugging easier.
- A small golden set is more useful than judging a few generated answers by
  eye, but the dataset and metrics must be described honestly.
- RAG guardrails should fail closed: an answer with an unknown citation should
  be rejected instead of shown to the user.

## AI-Assisted Development

This project was developed with AI-assisted coding tools. I used AI to discuss
design options, explain unfamiliar concepts, draft some documentation and test
cases, and review code. I remained responsible for choosing the architecture,
adapting the suggestions, running the application, checking the evaluation
results, and deciding what to keep.

The point of the project is not that every line was typed without help. The
point is that I can explain the pipeline, test its behavior, identify its
limitations, and continue improving it. More detail is available in
[`docs/ai-assisted-development.md`](docs/ai-assisted-development.md).

## License

This project is available under the [MIT License](LICENSE). The source law
dataset has its own license and is not included in this repository.
