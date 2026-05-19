"""Run the hand-test queries through the retrieval service.

A quick sanity check for Week 1-2 work — not the formal eval (that is the
golden set in Week 4). Each query in eval/example_queries.jsonl carries a loose
expectation (`expect_law`, optional `expect_unit`); this prints the top hits and
flags whether the expectation showed up.

    uv run python scripts/run_example_queries.py                  # hybrid
    uv run python scripts/run_example_queries.py --mode dense
    uv run python scripts/run_example_queries.py --mode bm25 --rerank

Needs Qdrant running (`make up`) and the index built (`make index`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

DEFAULT_QUERIES = ROOT_DIR / "eval" / "example_queries.jsonl"


def main() -> None:
    from app.config import get_settings
    from app.retrieval.service import RETRIEVAL_MODES, RetrievalService

    parser = argparse.ArgumentParser(description="Run hand-test queries.")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERIES)
    parser.add_argument("--mode", choices=RETRIEVAL_MODES, default="hybrid")
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    cases = _load_queries(args.queries)
    print(f"Loaded {len(cases)} queries from {args.queries}")
    print(f"mode={args.mode}  rerank={args.rerank}  top_k={args.top_k}")
    print("Loading retrieval service (first query loads the embedding model)...\n")

    service = RetrievalService(get_settings())

    hits = 0
    for index, case in enumerate(cases, start=1):
        query = case["query"]
        results = service.retrieve(query, mode=args.mode, top_k=args.top_k, rerank=args.rerank)
        hit = _expectation_met(results, case)
        hits += int(hit)

        print(f"[{index:2d}] {query}")
        print(f"     expect: {case['expect_law']} {case.get('expect_unit', '')}".rstrip())
        for rank, scored in enumerate(results, start=1):
            chunk = scored.chunk
            marker = "->" if _matches(chunk, case) else "  "
            print(
                f"   {marker} {rank}. [{chunk.law_code}] {chunk.citation[:70]}  "
                f"({scored.score:.4f})"
            )
        print(f"     {'HIT' if hit else 'MISS'}\n")

    print(f"Expectations met: {hits}/{len(cases)}")


def _load_queries(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"{path} not found.")
    cases = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _matches(chunk: object, case: dict) -> bool:
    law = getattr(chunk, "law_code", "")
    citation = getattr(chunk, "citation", "")
    if law != case["expect_law"]:
        return False
    unit = case.get("expect_unit", "")
    return not unit or unit in citation


def _expectation_met(results: list, case: dict) -> bool:
    return any(_matches(scored.chunk, case) for scored in results)


if __name__ == "__main__":
    main()
