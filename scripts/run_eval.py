"""Evaluate retrieval modes against the golden question set."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

DEFAULT_GOLDEN_SET = ROOT_DIR / "eval" / "golden_set.jsonl"
DEFAULT_OUT_DIR = ROOT_DIR / "eval" / "results"
NDCG_K = 10


@dataclass(frozen=True)
class RetrievalConfig:
    name: str
    mode: str
    rerank: bool = False
    exact_boost: bool = True


BASE_MODES: tuple[str, ...] = ("bm25", "dense", "hybrid")


def build_configs(*, boost: str, include_rerank: bool) -> list[RetrievalConfig]:
    """One config per mode and boost setting; `boost` is "on", "off" or "both"."""
    boost_values = {"on": [True], "off": [False], "both": [True, False]}[boost]
    modes = [(mode, mode, False) for mode in BASE_MODES]
    if include_rerank:
        modes.append(("hybrid_rerank", "hybrid", True))
    return [
        RetrievalConfig(
            name if exact_boost else f"{name}_no_boost",
            mode,
            rerank=rerank,
            exact_boost=exact_boost,
        )
        for exact_boost in boost_values
        for name, mode, rerank in modes
    ]


def main() -> None:
    from app.config import get_settings
    from app.retrieval.index_info import describe_index
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
    parser.add_argument(
        "--boost",
        choices=("on", "off", "both"),
        default="both",
        help="Run with the exact-reference boost on, off, or both (default).",
    )
    args = parser.parse_args()

    cases = _load_cases(args.golden_set)
    if not cases:
        raise SystemExit(f"{args.golden_set} is empty.")
    # Unanswerable questions have no relevant chunks, so ranking metrics are
    # undefined for them. They are counted here and scored by the answer eval.
    answerable = [case for case in cases if case["expected_source_chunks"]]
    unanswerable_count = len(cases) - len(answerable)
    fetch_k = max(args.top_k, NDCG_K)

    configs = build_configs(boost=args.boost, include_rerank=args.include_rerank)

    settings = get_settings()
    service = RetrievalService(settings)
    qdrant_ready, qdrant_error = _qdrant_ready(service)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report: dict[str, Any] = {
        "run_id": run_id,
        "golden_set": _display_path(args.golden_set),
        "case_count": len(cases),
        "answerable_cases": len(answerable),
        "unanswerable_cases": unanswerable_count,
        "top_k": args.top_k,
        "ndcg_k": NDCG_K,
        "index": describe_index(settings.index_chunks_path),
        "results": {},
    }

    for config in configs:
        if config.mode in {"dense", "hybrid"} and not qdrant_ready:
            report["results"][config.name] = {
                "mode": config.mode,
                "rerank": config.rerank,
                "exact_boost": config.exact_boost,
                "summary": _summarize([], total_cases=len(answerable)),
                "errors": [qdrant_error or "Qdrant collection is not ready."],
                "cases": [],
            }
            continue

        rows: list[dict[str, Any]] = []
        errors: list[str] = []
        for case in answerable:
            try:
                retrieved = service.retrieve(
                    case["query"],
                    mode=config.mode,  # type: ignore[arg-type]
                    top_k=fetch_k,
                    rerank=config.rerank,
                    exact_boost=config.exact_boost,
                )
            except Exception as exc:  # noqa: BLE001 - report unavailable configs cleanly
                errors.append(f"{case['id']}: {type(exc).__name__}: {exc}")
                continue

            retrieved_ids = [item.chunk.chunk_id for item in retrieved]
            rows.append(score_case(case, retrieved_ids, top_k=args.top_k))

        report["results"][config.name] = {
            "mode": config.mode,
            "rerank": config.rerank,
            "exact_boost": config.exact_boost,
            "summary": _summarize(rows, total_cases=len(answerable)),
            "errors": errors,
            "cases": rows,
        }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / f"retrieval_eval_{run_id}.json"
    md_path = args.out_dir / f"retrieval_eval_{run_id}.md"
    json_report = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    markdown_report = _markdown_report(report)
    json_path.write_text(json_report, encoding="utf-8")
    md_path.write_text(markdown_report, encoding="utf-8")

    latest_json = args.out_dir / "latest.json"
    latest_md = args.out_dir / "latest.md"
    latest_json.write_text(json_report, encoding="utf-8")
    latest_md.write_text(markdown_report, encoding="utf-8")

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
    if not isinstance(case["expected_source_chunks"], list):
        raise SystemExit(f"golden set line {line_number}: expected_source_chunks must be a list.")


def _index_line(index: dict[str, Any] | None) -> str:
    if not index:
        return "- Index: not recorded"
    return (
        f"- Index: {index['scope']} ({index['law_count']} laws, {index['chunk_count']:,} chunks; "
        f"scope {index['scope_source']})"
    )


def score_case(case: dict[str, Any], retrieved_ids: list[str], *, top_k: int) -> dict[str, Any]:
    from app.evaluation.metrics import (
        hit_at_k,
        ndcg_at_k,
        precision_at_k,
        recall_at_k,
        reciprocal_rank,
    )

    expected = set(case["expected_source_chunks"])
    return {
        "id": case["id"],
        "query": case["query"],
        "expected_source_chunks": sorted(expected),
        "retrieved_source_chunks": retrieved_ids,
        "hit": hit_at_k(retrieved_ids, expected, k=top_k),
        "precision_at_k": precision_at_k(retrieved_ids, expected, k=top_k),
        "recall_at_k": recall_at_k(retrieved_ids, expected, k=top_k),
        "mrr": reciprocal_rank(retrieved_ids, expected, k=top_k),
        "ndcg_at_10": ndcg_at_k(retrieved_ids, expected, k=NDCG_K),
    }


SUMMARY_METRICS = {
    "hit_rate": "hit",
    "mean_precision_at_k": "precision_at_k",
    "mean_recall_at_k": "recall_at_k",
    "mean_mrr": "mrr",
    "mean_ndcg_at_10": "ndcg_at_10",
}


def _summarize(rows: list[dict[str, Any]], *, total_cases: int) -> dict[str, float | int]:
    """Average each metric over all answerable cases; failed cases count as 0."""
    summary: dict[str, float | int] = {
        "completed_cases": len(rows),
        "total_cases": total_cases,
    }
    for name, key in SUMMARY_METRICS.items():
        total = sum(float(row[key]) for row in rows)
        summary[name] = total / total_cases if total_cases else 0.0
    return summary


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Retrieval Evaluation",
        "",
        f"- Run: `{report['run_id']}`",
        f"- Golden set: `{report['golden_set']}`",
        f"- Cases: {report['case_count']} "
        f"({report.get('answerable_cases', report['case_count'])} answerable, "
        f"{report.get('unanswerable_cases', 0)} unanswerable; only answerable cases are scored)",
        f"- Top-k: {report['top_k']}",
        _index_line(report.get("index")),
        "",
        "## Summary",
        "",
        "| Config | Boost | Completed | Hit@k | Precision@k | Recall@k | MRR@k | nDCG@10 "
        "| Errors |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in report["results"].items():
        summary = result["summary"]
        row_format = (
            "| {name} | {boost} | {completed}/{total} | {hit:.3f} | {precision:.3f} | "
            "{recall:.3f} | {mrr:.3f} | {ndcg:.3f} | {errors} |"
        )
        lines.append(
            row_format.format(
                name=name,
                boost="on" if result.get("exact_boost", True) else "off",
                completed=summary["completed_cases"],
                total=summary["total_cases"],
                hit=summary["hit_rate"],
                precision=summary["mean_precision_at_k"],
                recall=summary["mean_recall_at_k"],
                mrr=summary["mean_mrr"],
                ndcg=summary["mean_ndcg_at_10"],
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
