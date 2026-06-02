# Data Sources

## Chosen Domain

GermanLawRAG uses German legal text as its domain.

Primary source family:

- Gesetze im Internet
- Bundestag law text data, referred to in this project as `bundestag/gesetze`

## Local Dataset

The raw dataset is present at:

```text
data/raw/german-laws/
```

This is a Markdown repository converted from the XML source at Gesetze im Internet. Each law generally lives at:

```text
data/raw/german-laws/<first-character>/<law-slug>/index.md
```

Each `index.md` contains YAML-like front matter:

- `Title`
- `jurabk`
- `origslug`
- `slug`

The ingestion code uses those fields to preserve law title, abbreviation, slug, and source URL metadata.

## Raw Data Policy

Raw source files belong in `data/raw/` and are intentionally gitignored. This keeps the repository light and avoids committing large local corpora.

Recommended local layout:

```text
data/raw/
└── german-laws/
```

## Normalized Output

The ingestion pipeline writes processed artifacts to:

```text
data/processed/
├── documents.jsonl
└── chunks.jsonl
```

Each chunk should preserve enough metadata for citations:

- `chunk_id`
- `source_id`
- `title`
- `text`
- `start_char`
- `end_char`
- `law_code`, when available
- `section`, when available
- `source_url`, when available
- `citation`, for example `GG Art 5`
- `hierarchy`, for example `["I. - Die Grundrechte", "Art 5"]`

## Citation Goal

Answers should cite stable chunk IDs first. Later, citations can include law title, section, paragraph, and source URL when the parser extracts those fields reliably.
