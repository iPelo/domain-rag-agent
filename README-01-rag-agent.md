# DomainRAG — Production-grade Retrieval-Augmented AI Assistant

> An end-to-end RAG + agent system over **[YOUR DOMAIN]**. Hybrid retrieval, reranking, a real evaluation harness, observability, and a deployed demo.

**Status:** 🚧 In development
**Live demo:** _coming_
**Tech:** Python · FastAPI · Qdrant · LangGraph · Next.js · Docker · Fly.io

---

## The Problem

LLMs hallucinate when asked about specific documents. Naive RAG (chunk + embed + retrieve + stuff) helps but has a lot of failure modes that almost no one in a portfolio bothers to measure. This project builds a real RAG + agent system for **one specific domain** and rigorously evaluates each architectural choice.

The differentiator on your portfolio is **not the chatbot** — it's the evaluation harness and the engineering decisions you can defend.

## Step 0: Pick your domain (do this before any code)

Pick **one** and write it in below — delete the rest:

- [ ] **University course materials** — your professors' slides, recordings, problem sets, past exams
- [x] **German legal texts** — gesetze-im-internet.de (BGB, StGB, GG…). Public domain, real content.
- [ ] **Bundestag transcripts** — open-discourse.org has structured parliamentary debates
- [ ] **ArXiv papers in one subfield** — e.g. "RL for robotics 2022–2025"
- [ ] **A large open-source project's docs + source comments** — e.g. all of FastAPI, or PyTorch

**Your chosen domain:** GermanLawRAG — German legal texts from Gesetze im Internet / Bundestag law text data

Why this matters: a generic "chat with PDFs" project signals nothing. A focused, defensible domain choice signals taste and judgment.

## Architecture

```
[ Raw data ]
     │
     ▼
[ Ingestion: chunk + embed ] ──► [ Qdrant (vectors) ]
                                 [ BM25 index      ]
     │
     ▼
[ FastAPI service ]
     ├─ Hybrid retrieval (BM25 + dense + RRF + rerank)
     ├─ Agent loop: tools = {retrieve, calc, web_search}
     ├─ Observability → Langfuse
     └─ /eval endpoint (re-runs golden set)
     │
     ▼
[ Next.js chat UI — streaming, inline citations ]
```

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | Standard for AI/ML |
| Pkg manager | `uv` | 10–100× faster than pip/poetry |
| API | FastAPI | Async, typed, auto OpenAPI |
| Vector DB | Qdrant | Rust core, great filtering, easy local Docker |
| Embeddings | `bge-m3` or `nomic-embed-text` | Multilingual (matters for German) |
| Reranker | `bge-reranker-v2-m3` | Big quality boost, runs locally on M4 |
| LLM | Hosted LLM + Ollama (Llama 3.1 8B) fallback | Cost vs. quality trade-off |
| Orchestration | LangGraph **or** hand-rolled | Hand-rolled is more impressive |
| Observability | Langfuse (self-hosted Docker) | Free, OSS |
| Frontend | Next.js 14 + Tailwind | Standard, fast |
| Deploy | Fly.io or Hugging Face Spaces | Free tier viable |

## Roadmap

### Phase 1 — Foundation (Week 1)
- [ ] Pick the domain, collect raw data (script, not manual)
- [ ] Set up project with `uv init` + ruff + mypy + pre-commit
- [ ] Ingestion: load → chunk → embed → write to Qdrant
- [ ] Basic top-k cosine retrieval endpoint
- [ ] Write 10 example queries to test by hand

### Phase 2 — Retrieval quality (Week 2)
- [ ] Add BM25 index (`rank_bm25` or Tantivy)
- [ ] Hybrid retrieval with Reciprocal Rank Fusion
- [ ] Add a cross-encoder reranker stage
- [ ] Try 3 chunking strategies (fixed, recursive, semantic) and **document trade-offs**

### Phase 3 — Generation + Agent (Week 3)
- [ ] Stuff top-k chunks into a generation prompt
- [ ] Force model to cite chunk IDs in every answer
- [ ] Agent loop: model can call `retrieve(query)` multiple times before answering
- [ ] Add a second tool (calculator, date math, or web search)

### Phase 4 — Evaluation ⭐ THE PART THAT MAKES THIS A PORTFOLIO PROJECT (Week 4)
- [ ] Hand-build a **golden set** of 30–50 `(query, expected_answer, expected_source_chunks)` triples
- [ ] Metrics: retrieval precision@k, MRR, faithfulness (LLM-as-judge), answer relevance
- [ ] Run eval, write results table to `eval/results/`, commit it
- [ ] **Comparison table:** naive RAG vs. hybrid vs. hybrid+rerank vs. agent loop. This goes in your portfolio writeup.

### Phase 5 — Observability + hardening (Week 5)
- [ ] Self-host Langfuse via `docker compose`
- [ ] Instrument every LLM call and retrieval
- [ ] Cost tracking per request
- [ ] Rate limiting + API key auth

### Phase 6 — Frontend + deploy (Week 6)
- [ ] Next.js chat UI with streaming and inline citation chips
- [ ] Dockerize backend + frontend
- [ ] One-shot deploy script to Fly.io
- [ ] Record a 90-second demo video for your portfolio

## What I'm trying to learn / demonstrate

- Real LLM application engineering, not just API calls
- Honest evaluation of retrieval and generation
- Production concerns: cost, latency, observability
- Hybrid retrieval and articulating its trade-offs

## Target Project Structure

```
domain-rag-agent/
├── README.md
├── pyproject.toml
├── docker-compose.yml          # qdrant + langfuse + postgres
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── ingestion/
│   │   ├── retrieval/          # bm25, dense, rrf, rerank
│   │   ├── agent/              # loop, tools, prompts
│   │   ├── eval/               # harness + metrics
│   │   └── config.py
│   └── tests/
├── frontend/                   # Next.js
├── data/
│   ├── raw/                    # gitignored
│   └── processed/              # gitignored
├── eval/
│   ├── golden_set.jsonl
│   └── results/
└── docs/
    ├── architecture.md
    └── decisions.md            # ← the page senior engineers will read
```

## Decisions to document in `docs/decisions.md`

This file is what makes the difference between "another LLM project" and "this candidate thinks." For each, write 1–3 paragraphs:

1. Chunking strategy (and what you tried that didn't work)
2. Embedding model choice and language considerations
3. Hybrid fusion method (RRF vs. weighted)
4. Why agent loop vs. pure RAG (or vice versa)
5. Eval methodology limitations
6. Cost/latency trade-offs in production

## Resources to read first

- Anthropic, "Contextual Retrieval" (blog post)
- LlamaIndex retrieval docs (read even if you don't use the library)
- RAGAS paper, for evaluation metric ideas
- Qdrant tutorials
- Langfuse self-hosting docs

## License

MIT
