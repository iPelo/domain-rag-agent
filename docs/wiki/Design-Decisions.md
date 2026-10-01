# Design Decisions

## Markdown as the Initial Source

The project starts from the `bundestag/gesetze` Markdown conversion because it
is easy to inspect and preserves useful headings. The trade-off is dependence
on conversion structure instead of the richer upstream XML.

## Legal-Heading Chunking

German laws already contain meaningful boundaries such as articles and
sections. Keeping those units together improves citations and makes retrieved
text easier to inspect. Very long sections use overlapping recursive splitting
as a fallback.

## Hybrid Retrieval

BM25 performs well on exact references and legal terminology. Dense retrieval
helps when a user paraphrases the source. Reciprocal rank fusion combines their
rank positions without requiring the raw scores to use the same scale.

## Optional Reranking

A cross-encoder can improve ordering because it reads the query and candidate
together. It is optional because it increases latency and model size.

## Lazy Model Loading

Embedding and reranking weights load only when needed. Health checks, BM25-only
tests, and application startup therefore avoid paying the model-loading cost.

## Fail-Closed Citations

Generated answers must cite retrieved chunk IDs. If the model returns an unknown
ID or no citation, the API rejects the answer. Returning an error is safer than
displaying a source reference that the system cannot verify.

## Curated Development Index

The default index uses a small group of major codes so local indexing stays
manageable. Full-corpus indexing remains available through `make index-all`.
