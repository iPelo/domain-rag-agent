"""Run the golden retrieval set and write a compact report.

The runner scores each retrieval configuration against `eval/golden_set.jsonl`
using exact chunk-id matches. BM25 can run from the local chunk file alone.
Dense and hybrid runs require Qdrant to be running and indexed.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

DEFAULT_GOLDEN_SET = ROOT_DIR / "eval" / "golden_set.jsonl"
DEFAULT_OUT_DIR = ROOT_DIR / "eval" / "results"


@dataclass(frozen=True)
class RetrievalConfig:
    name: str
    mode: str
    rerank: bool = False


DEFAULT_CONFIGS: tuple[RetrievalConfig, ...] = (
    RetrievalConfig("bm25", "bm25"),
    RetrievalConfig("dense", "dense"),
    RetrievalConfig("hybrid", "hybrid"),
)


def main() -> None:
    from app.config import get_settings
    from app.eval.metrics import mean_reciprocal_rank, precision_at_k
    from app.retrieval.service import RetrievalService

    parser = argparse.ArgumentParser(description="Run the golden retrieval set.")
    parser.add_argument("--golden-set", type=Path, default=DEFAULT_GOLDEN_SET)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--include-rerank",
        action="store_true",
        help="Also score hybrid+rerank. This loads the reranker model.",
    )
    args = parser.parse_args()

    cases = _load_cases(args.golden_set)
    if not cases:
        raise SystemExit(f"{args.golden_set} is empty.")

    configs = list(DEFAULT_CONFIGS)
    if args.include_rerank:
        configs.append(RetrievalConfig("hybrid_rerank", "hybrid", rerank=True))

    service = RetrievalService(get_settings())
    qdrant_ready, qdrant_error = _qdrant_ready(service)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report: dict[str, Any] = {
        "run_id": run_id,
        "golden_set": _display_path(args.golden_set),
        "case_count": len(cases),
        "top_k": args.top_k,
        "results": {},
    }

    for config in configs:
        if config.mode in {"dense", "hybrid"} and not qdrant_ready:
            report["results"][config.name] = {
                "mode": config.mode,
                "rerank": config.rerank,
                "summary": _summarize([], total_cases=len(cases)),
                "errors": [qdrant_error or "Qdrant collection is not ready."],
                "cases": [],
            }
            continue

        rows: list[dict[str, Any]] = []
        errors: list[str] = []
        for case in cases:
            expected = set(case["expected_source_chunks"])
            try:
                retrieved = service.retrieve(
                    case["query"],
                    mode=config.mode,  # type: ignore[arg-type]
                    top_k=args.top_k,
                    rerank=config.rerank,
                )
            except Exception as exc:  # noqa: BLE001 - report unavailable configs cleanly
                errors.append(f"{case['id']}: {type(exc).__name__}: {exc}")
                continue

            retrieved_ids = [item.chunk.chunk_id for item in retrieved]
            rows.append(
                {
                    "id": case["id"],
                    "query": case["query"],
                    "expected_source_chunks": sorted(expected),
                    "retrieved_source_chunks": retrieved_ids,
                    "hit": bool(expected.intersection(retrieved_ids[: args.top_k])),
                    "precision_at_k": precision_at_k(
                        retrieved_ids,
                        expected,
                        k=args.top_k,
                    ),
                    "mrr": mean_reciprocal_rank(retrieved_ids, expected),
                }
            )

        report["results"][config.name] = {
            "mode": config.mode,
            "rerank": config.rerank,
            "summary": _summarize(rows, total_cases=len(cases)),
            "errors": errors,
            "cases": rows,
        }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"retrieval_eval_{run_id}.json"
    md_path = args.out_dir / f"retrieval_eval_{run_id}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_markdown_report(report), encoding="utf-8")

    latest_json = args.out_dir / "latest.json"
    latest_md = args.out_dir / "latest.md"
    latest_payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    latest_json.write_text(latest_payload, encoding="utf-8")
    latest_md.write_text(_markdown_report(report), encoding="utf-8")

    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")


def _qdrant_ready(service: Any) -> tuple[bool, str | None]:
    try:
        stats = service.stats()
    except Exception as exc:  # noqa: BLE001 - Qdrant transport errors vary by client version
        return False, f"Qdrant unavailable: {type(exc).__name__}: {exc}"
    if not stats.collection_ready:
        return False, f"Qdrant collection '{stats.collection}' is missing."
    if stats.qdrant_points <= 0:
        return False, f"Qdrant collection '{stats.collection}' has no points."
    return True, None


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


def _load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"{path} not found.")
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            case = json.loads(line)
            _validate_case(case, line_number)
            cases.append(case)
    return cases


def _validate_case(case: dict[str, Any], line_number: int) -> None:
    required = {"id", "query", "expected_answer", "expected_source_chunks"}
    missing = sorted(required - set(case))
    if missing:
        raise SystemExit(f"golden set line {line_number} missing: {', '.join(missing)}")
    if not isinstance(case["expected_source_chunks"], list) or not case["expected_source_chunks"]:
        raise SystemExit(f"golden set line {line_number} needs expected_source_chunks.")


def _summarize(rows: list[dict[str, Any]], *, total_cases: int) -> dict[str, float | int]:
    completed = len(rows)
    if not rows:
        return {
            "completed_cases": completed,
            "total_cases": total_cases,
            "hit_rate": 0.0,
            "mean_precision_at_k": 0.0,
            "mean_mrr": 0.0,
        }
    return {
        "completed_cases": completed,
        "total_cases": total_cases,
        "hit_rate": sum(1 for row in rows if row["hit"]) / total_cases,
        "mean_precision_at_k": statistics.fmean(row["precision_at_k"] for row in rows),
        "mean_mrr": statistics.fmean(row["mrr"] for row in rows),
    }


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Retrieval Evaluation",
        "",
        f"- Run: `{report['run_id']}`",
        f"- Golden set: `{report['golden_set']}`",
        f"- Cases: {report['case_count']}",
        f"- Top-k: {report['top_k']}",
        "",
        "## Summary",
        "",
        "| Config | Completed | Hit rate | Mean precision@k | Mean MRR | Errors |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, result in report["results"].items():
        summary = result["summary"]
        row_format = (
            "| {name} | {completed}/{total} | {hit:.3f} | "
            "{precision:.3f} | {mrr:.3f} | {errors} |"
        )
        lines.append(
            row_format.format(
                name=name,
                completed=summary["completed_cases"],
                total=summary["total_cases"],
                hit=summary["hit_rate"],
                precision=summary["mean_precision_at_k"],
                mrr=summary["mean_mrr"],
                errors=len(result["errors"]),
            )
        )

    for name, result in report["results"].items():
        if not result["errors"]:
            continue
        lines.extend(["", f"## {name} Errors", ""])
        lines.extend(f"- {error}" for error in result["errors"][:10])
        if len(result["errors"]) > 10:
            lines.append(f"- ... {len(result['errors']) - 10} more")

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
