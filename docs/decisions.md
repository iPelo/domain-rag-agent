# Decisions

This file records the engineering decisions behind the current implementation.

## 1. Domain

Chosen domain: German legal texts.

Reason: the corpus is specific, multilingual retrieval matters, and answer quality can be checked against exact source passages.

## 2. Initial Data Strategy

Start with the local `bundestag/gesetze` Markdown clone under `data/raw/german-laws/`.

The parser reads each law's `index.md`, extracts YAML-like front matter, and preserves `jurabk`, `slug`, `origslug`, source path, and an inferred Gesetze-im-Internet URL.

Trade-off: this is source-specific enough to create good citations quickly, but it depends on the Markdown conversion rather than the richer upstream XML semantics.

## 3. Chunking Strategy

Initial strategy: legal-heading chunks with fixed-size fallback splitting.

Why: German laws are naturally organized by headings such as `§ 1`, `Art 5`, `Präambel`, and `Anlage`. Chunking by those headings gives more meaningful retrieval results and citations than arbitrary text windows. If a legal unit is too long, it is split into overlapping character chunks.

The comparison script also measures fixed-size and paragraph-aware chunking so changes can be discussed with numbers instead of preference.

## 4. Retrieval Strategy

Initial target: dense retrieval plus BM25, fused with reciprocal rank fusion.

Why: legal queries often contain exact terms, section numbers, abbreviations, and paraphrases. BM25 helps exact matching; embeddings help semantic matching; RRF avoids tuning weights too early.

## 5. Evaluation

The project should use a hand-built golden set of 30-50 examples with expected answer text and expected source chunks.

The first 10 examples can be rough, but the final set should include exact citation expectations.
