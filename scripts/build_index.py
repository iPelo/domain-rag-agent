"""Build the dense vector index in Qdrant.

Reads the processed chunk corpus, optionally narrows it to the curated subset of
major federal codes, embeds every chunk with the configured model, and upserts
the vectors into the Qdrant collection.

    uv run python scripts/build_index.py                 # curated subset (~15k chunks)
    uv run python scripts/build_index.py --all           # full corpus (~178k chunks)
    uv run python scripts/build_index.py --limit 200     # quick smoke test

The curated chunk file it writes (`--out`) is what the API loads at runtime for
the BM25 index and payload hydration, so this script is the single entry point
for refreshing the index.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))


def main() -> None:
    from app.config import get_settings
    from app.ingestion.curated import CURATED_LAW_SLUGS
    from app.retrieval.dense import DenseRetriever
    from app.retrieval.embeddings import EmbeddingModel

    settings = get_settings()

    parser = argparse.ArgumentParser(description="Embed chunks and upsert into Qdrant.")
    parser.add_argument(
        "--chunks",
        type=Path,
        default=settings.data_processed_dir / "chunks.jsonl",
        help="Processed chunk corpus produced by build_chunks.py.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=settings.index_chunks_path,
        help="Where to write the chunk file the API loads at runtime.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Index the whole corpus instead of the curated subset.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Cap chunks (smoke test).")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=512,
        help="Chunks embedded and upserted per batch.",
    )
    args = parser.parse_args()

    if not args.chunks.exists():
        raise SystemExit(f"{args.chunks} not found — run `make chunks` first.")

    selected = _load_chunks(args.chunks, curated_only=not args.all, limit=args.limit)
    if not selected:
        raise SystemExit("No chunks selected — check --chunks / curated slug list.")

    scope = "full corpus" if args.all else f"curated subset ({len(CURATED_LAW_SLUGS)} codes)"
    print(f"Selected {len(selected):,} chunks ({scope}).")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for record in selected:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"Wrote runtime chunk file -> {args.out}")

    embedder = EmbeddingModel(
        settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
    )
    print(f"Loading embedding model {settings.embedding_model} (first run downloads it)...")
    dim = embedder.dimension
    print(f"Embedding dimension: {dim}")

    retriever = DenseRetriever(settings.qdrant_url, settings.qdrant_collection)
    retriever.recreate_collection(dim=dim)
    print(f"Recreated Qdrant collection '{settings.qdrant_collection}'.")

    started = time.monotonic()
    done = 0
    for batch in _iter_batches(selected, args.batch_size):
        vectors = embedder.encode([record["text"] for record in batch])
        _upsert_with_retry(
            retriever,
            chunk_ids=[record["chunk_id"] for record in batch],
            vectors=vectors,
            payloads=[_payload(record) for record in batch],
        )
        done += len(batch)
        rate = done / max(time.monotonic() - started, 1e-6)
        print(f"  embedded + upserted {done:,}/{len(selected):,}  ({rate:.0f} chunks/s)")

    elapsed = time.monotonic() - started
    point_count = retriever.count()
    if point_count != len(selected):
        raise SystemExit(
            f"Index incomplete: Qdrant has {point_count:,} points, "
            f"but {len(selected):,} chunks were selected."
        )
    print(f"Done in {elapsed:.0f}s. Qdrant points: {point_count:,}")


def _upsert_with_retry(
    retriever,
    *,
    chunk_ids: list[str],
    vectors: list[list[float]],
    payloads: list[dict],
    attempts: int = 6,
) -> None:
    """Upsert a batch, tolerating a transient Qdrant restart.

    Embedding is the expensive step, so a brief Qdrant outage should not throw
    away a batch's work. The container restarts itself (`restart: unless-stopped`);
    here we reconnect and retry with exponential backoff.
    """
    for attempt in range(1, attempts + 1):
        try:
            retriever.upsert(chunk_ids=chunk_ids, vectors=vectors, payloads=payloads)
            return
        except Exception as exc:  # noqa: BLE001 - any Qdrant/transport error is retryable
            if attempt == attempts:
                raise
            wait = min(2**attempt, 30)
            print(f"  upsert failed ({type(exc).__name__}); reconnecting, retry in {wait}s")
            time.sleep(wait)
            retriever.reconnect()


def _load_chunks(path: Path, *, curated_only: bool, limit: int | None) -> list[dict]:
    from app.ingestion.curated import is_curated_slug

    records: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            slug = record.get("metadata", {}).get("slug")
            if curated_only and not is_curated_slug(slug):
                continue
            records.append(record)
            if limit is not None and len(records) >= limit:
                break
    return records


def _payload(record: dict) -> dict:
    metadata = record.get("metadata", {})
    return {
        "law_code": metadata.get("law_code", ""),
        "slug": metadata.get("slug", ""),
    }


def _iter_batches(items: list[dict], batch_size: int):
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


if __name__ == "__main__":
    main()
