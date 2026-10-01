# Architecture

## Data Flow

```text
bundestag/gesetze Markdown
        |
        v
load metadata and text
        |
        v
split around legal headings
        |
        v
documents.jsonl + chunks.jsonl
        |
        +--------------------+
        |                    |
        v                    v
   BM25 index          Qdrant vectors
        |                    |
        +---------+----------+
                  v
       reciprocal rank fusion
                  |
          optional reranker
                  |
          retrieved sources
                  |
       optional answer model
```

## Ingestion

`app.ingestion` reads each law's `index.md`, extracts frontmatter, and preserves
the law abbreviation, source slug, title, and source URL. The production
chunker uses Markdown headings as legal boundaries. Sections that exceed the
size limit fall back to overlapping recursive splitting.

Each chunk receives a stable ID and citation metadata. Stable IDs allow the
vector index to be rebuilt without creating duplicate records.

## Retrieval

The retrieval service owns three paths:

- **BM25** handles exact terms, abbreviations, and section numbers.
- **Dense search** embeds the query and searches Qdrant by cosine similarity.
- **Hybrid search** combines both ranked lists with reciprocal rank fusion.

If reranking is enabled, the service fetches a wider candidate pool and asks a
cross-encoder to score each query/chunk pair before returning the final top-k.

Queries that explicitly name a law and section receive a deterministic exact
reference boost. This prevents an exact citation such as `§ 433 BGB` from being
buried under semantically similar sections.

## Answer Generation

The answer service retrieves sources, formats them into the model prompt, and
validates every returned chunk citation. Unknown or missing citations cause the
request to fail instead of returning an ungrounded answer.

This validation proves that a cited ID was retrieved. It does not prove that
every sentence in the answer is supported by the cited passage.

## Main Modules

| Module | Responsibility |
|---|---|
| `app.ingestion` | Loading, metadata parsing, and chunking |
| `app.retrieval` | BM25, vector search, fusion, and reranking |
| `app.generation` | Prompt construction, model call, citation validation |
| `app.eval` | Retrieval metrics |
| `app.main` | FastAPI routes and error mapping |
