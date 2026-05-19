"""Compare chunking strategies on a sample of German laws.

Runs the three strategies (`legal-heading`, `fixed`, `recursive`) over the same
laws with the same size budget, so the only variable is the boundary logic, and
prints a Markdown stats table. The numbers feed the trade-off write-up in
docs/decisions.md.

    uv run python scripts/compare_chunking.py
    uv run python scripts/compare_chunking.py --raw-dir data/raw/german-laws
"""

from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

# Varied in size and structure: a short constitution, two large codes, two
# mid-size codes.
SAMPLE_SLUGS = ("gg", "bgb", "stgb", "stpo", "hgb", "urhg")
STRATEGIES = ("legal-heading", "fixed", "recursive")
CHUNK_SIZE = 1600
OVERLAP = 180


def main() -> None:
    from app.ingestion.chunking import chunk_document
    from app.ingestion.loaders import load_local_documents

    parser = argparse.ArgumentParser(description="Compare chunking strategies.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/german-laws"))
    args = parser.parse_args()

    documents = []
    for slug in SAMPLE_SLUGS:
        law_dir = args.raw_dir / slug[0] / slug
        loaded = load_local_documents(law_dir) if law_dir.exists() else []
        if not loaded:
            print(f"  (skipped: {slug} not found at {law_dir})")
            continue
        documents.extend(loaded)

    if not documents:
        raise SystemExit("No sample laws found — check --raw-dir.")

    print(
        f"Sample: {len(documents)} laws "
        f"({', '.join(d.metadata.get('law_code', '?') for d in documents)})"
    )
    print(f"Size budget: chunk_size={CHUNK_SIZE}, overlap={OVERLAP}\n")

    rows = []
    for strategy in STRATEGIES:
        lengths: list[int] = []
        mid_sentence_starts = 0
        for document in documents:
            for chunk in chunk_document(
                document,
                strategy=strategy,
                chunk_size=CHUNK_SIZE,
                overlap=OVERLAP,
            ):
                lengths.append(len(chunk.text))
                if _starts_mid_sentence(chunk.text):
                    mid_sentence_starts += 1
        rows.append(_summarize(strategy, lengths, mid_sentence_starts))

    _print_table(rows)


def _starts_mid_sentence(text: str) -> bool:
    """A chunk whose first letter is lowercase was almost certainly cut mid-sentence."""
    for char in text.lstrip():
        if char.isalpha():
            return char.islower()
    return False


def _summarize(strategy: str, lengths: list[int], mid_sentence_starts: int) -> dict[str, object]:
    if not lengths:
        return {"strategy": strategy, "chunks": 0}
    return {
        "strategy": strategy,
        "chunks": len(lengths),
        "mean": statistics.mean(lengths),
        "median": statistics.median(lengths),
        "p90": sorted(lengths)[min(len(lengths) - 1, int(0.9 * len(lengths)))],
        "stdev": statistics.pstdev(lengths),
        "max": max(lengths),
        "mid_pct": 100.0 * mid_sentence_starts / len(lengths),
    }


def _print_table(rows: list[dict[str, object]]) -> None:
    header = [
        "Strategy",
        "Chunks",
        "Mean",
        "Median",
        "P90",
        "StdDev",
        "Max",
        "Mid-sentence start %",
    ]
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(["---"] * len(header)) + "|")
    for row in rows:
        if not row.get("chunks"):
            print(f"| {row['strategy']} | 0 | - | - | - | - | - | - |")
            continue
        print(
            f"| {row['strategy']} | {row['chunks']} | {row['mean']:.0f} | "
            f"{row['median']:.0f} | {row['p90']} | {row['stdev']:.0f} | "
            f"{row['max']} | {row['mid_pct']:.1f}% |"
        )


if __name__ == "__main__":
    main()
