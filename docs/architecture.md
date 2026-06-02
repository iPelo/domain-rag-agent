# Architecture

GermanLawRAG is split into four layers:

1. Ingestion: read Bundestag/Gesetze Markdown files, normalize text, preserve source metadata, and chunk by legal heading.
2. Retrieval: combine dense vector search with BM25, then fuse rankings with reciprocal rank fusion.
3. Generation/agent: answer only from retrieved chunks and cite chunk IDs.
4. Evaluation: measure retrieval quality and answer grounding against a hand-built golden set.

## Backend Modules

- `app.ingestion`: raw document loading, parsing, chunking, and processed JSONL output.
- `app.retrieval`: BM25, dense retrieval, ranking fusion, and later reranking.
- `app.agent`: prompts and tools used by the answering loop.
- `app.eval`: deterministic metrics and future model-graded evaluation.

## Data Flow

```text
data/raw/german-laws/*/index.md
  -> ingestion pipeline
  -> data/processed/documents.jsonl + data/processed/chunks.jsonl
  -> Qdrant + BM25
  -> API responses
```

## First Vertical Slice

The first working slice should be:

1. Keep the cloned German law repository in `data/raw/german-laws/`.
2. Run the ingestion pipeline to create legal-heading chunks.
3. Insert chunks into Qdrant.
4. Add a `/retrieve` endpoint.
5. Test 10 known German legal questions by hand.
