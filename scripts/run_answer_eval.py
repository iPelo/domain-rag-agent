"""Evaluate generated answers: citations per claim, abstention, optional LLM judge."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

DEFAULT_ANSWER_SET = ROOT_DIR / "eval" / "answer_set.jsonl"
DEFAULT_OUT_DIR = ROOT_DIR / "eval" / "results"


def main() -> None:
    from app.config import get_settings
    from app.generation.chat_client import ModelConfigurationError, build_chat_client
    from app.generation.service import GenerationService
    from app.retrieval.index_info import describe_index
    from app.retrieval.service import RETRIEVAL_MODES, RetrievalService

    parser = argparse.ArgumentParser(description="Run the answer evaluation set.")
    parser.add_argument("--answer-set", type=Path, default=DEFAULT_ANSWER_SET)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--mode", choices=RETRIEVAL_MODES, default="hybrid")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Grade answered cases against expected_answer with an LLM judge.",
    )
    args = parser.parse_args()

    cases = _load_cases(args.answer_set)
    settings = get_settings()
    try:
        chat = build_chat_client(settings)
        judge = build_chat_client(settings.judge_settings()) if args.judge else None
    except ModelConfigurationError as exc:
        raise SystemExit(f"Answer eval needs a chat model: {exc}") from exc

    retrieval = RetrievalService(settings)
    generation = GenerationService(retrieval, chat)

    rows = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index:2d}/{len(cases)}] {case['id']}")
        rows.append(_run_case(case, generation, judge, args))

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report: dict[str, Any] = {
        "run_id": run_id,
        "answer_set": _display_path(args.answer_set),
        "mode": args.mode,
        "rerank": args.rerank,
        "top_k": args.top_k,
        "model": settings.model_name,
        "judge_model": settings.judge_settings().model_name if args.judge else None,
        "index": describe_index(settings.index_chunks_path),
        "summary": summarize(rows),
        "cases": rows,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_report = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    markdown_report = _markdown_report(report)
    for stem in (f"answer_eval_{run_id}", "answer_latest"):
        (args.out_dir / f"{stem}.json").write_text(json_report, encoding="utf-8")
        (args.out_dir / f"{stem}.md").write_text(markdown_report, encoding="utf-8")
    print(f"Wrote {args.out_dir / f'answer_eval_{run_id}.md'}")


def _run_case(case: dict[str, Any], generation: Any, judge: Any, args: Any) -> dict[str, Any]:
    from app.evaluation.answer_checks import (
        JUDGE_SYSTEM_PROMPT,
        build_judge_prompt,
        check_citations,
        parse_judge_response,
    )
    from app.generation.service import CitationValidationError

    expected = set(case["expected_source_chunks"])
    answerable = bool(expected)
    row: dict[str, Any] = {"id": case["id"], "query": case["query"], "answerable": answerable}

    try:
        result = generation.answer(
            case["query"], mode=args.mode, top_k=args.top_k, rerank=args.rerank
        )
    except CitationValidationError as exc:
        # The service's own check rejected the answer (no or unknown citations).
        return {**row, "status": "rejected", "error": str(exc), "abstained_correctly": False}
    except Exception as exc:  # noqa: BLE001 - record model/transport failures per case
        return {
            **row,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "abstained_correctly": False,
        }

    row["answer"] = result.answer
    row["status"] = "no_answer" if result.no_answer else "answered"
    row["abstained_correctly"] = result.no_answer != answerable
    if result.no_answer:
        return row

    source_ids = {source.chunk.chunk_id for source in result.sources}
    cited = [citation.chunk_id for citation in result.citations]
    check = check_citations(result.answer, source_ids)
    row.update(
        {
            "cited_chunks": cited,
            "claims": len(check.claims),
            "uncited_claims": check.uncited_claims,
            "invalid_citations": check.invalid_citations,
            "all_claims_cited": check.all_claims_cited,
            "citation_coverage": check.citation_coverage,
            "cites_expected_chunk": bool(expected.intersection(cited)) if answerable else None,
        }
    )

    if judge is not None and answerable:
        cited_texts = [
            f"[{source.chunk.chunk_id}]\n{source.chunk.text}"
            for source in result.sources
            if source.chunk.chunk_id in cited
        ]
        try:
            raw = judge.complete(
                system_prompt=JUDGE_SYSTEM_PROMPT,
                user_prompt=build_judge_prompt(
                    query=case["query"],
                    expected_answer=case["expected_answer"],
                    answer=result.answer,
                    sources=cited_texts,
                ),
            )
            row["judge"] = parse_judge_response(raw)
        except Exception as exc:  # noqa: BLE001 - a failed grade should not stop the run
            row["judge"] = {"score": None, "reason": f"{type(exc).__name__}: {exc}"}
    return row


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    answered = [row for row in rows if row["status"] == "answered"]
    answerable_answered = [row for row in answered if row["answerable"]]
    scores = [
        row["judge"]["score"]
        for row in answered
        if row.get("judge") and row["judge"]["score"] is not None
    ]
    return {
        "cases": len(rows),
        "answerable_cases": sum(1 for row in rows if row["answerable"]),
        "answered": len(answered),
        "no_answer": sum(1 for row in rows if row["status"] == "no_answer"),
        "rejected_by_citation_check": sum(1 for row in rows if row["status"] == "rejected"),
        "errors": sum(1 for row in rows if row["status"] == "error"),
        "abstention_accuracy": _mean([float(row["abstained_correctly"]) for row in rows]),
        "all_claims_cited_rate": _mean([float(row["all_claims_cited"]) for row in answered]),
        "mean_citation_coverage": _mean([row["citation_coverage"] for row in answered]),
        "cites_expected_chunk_rate": _mean(
            [float(row["cites_expected_chunk"]) for row in answerable_answered]
        ),
        "judged_cases": len(scores),
        "mean_judge_score": _mean([float(score) for score in scores]),
    }


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    index = report["index"]
    lines = [
        "# Answer Evaluation",
        "",
        f"- Run: `{report['run_id']}`",
        f"- Answer set: `{report['answer_set']}` ({summary['cases']} cases, "
        f"{summary['answerable_cases']} answerable)",
        f"- Retrieval: {report['mode']}, top-k {report['top_k']}, "
        f"rerank {'on' if report['rerank'] else 'off'}",
        f"- Model: `{report['model']}`; judge: `{report['judge_model'] or 'off'}`",
        f"- Index: {index['scope']} ({index['law_count']} laws, {index['chunk_count']:,} chunks)",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Answered / no answer / rejected / errors | {summary['answered']} / "
        f"{summary['no_answer']} / {summary['rejected_by_citation_check']} / "
        f"{summary['errors']} |",
        f"| Abstention accuracy (all cases) | {_fmt(summary['abstention_accuracy'])} |",
        f"| Every claim cited (answered) | {_fmt(summary['all_claims_cited_rate'])} |",
        f"| Mean claim citation coverage | {_fmt(summary['mean_citation_coverage'])} |",
        f"| Cites an expected chunk | {_fmt(summary['cites_expected_chunk_rate'])} |",
        f"| Mean judge score (1-5, {summary['judged_cases']} judged) | "
        f"{_fmt(summary['mean_judge_score'])} |",
        "",
    ]
    return "\n".join(lines)


def _load_cases(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"{path} not found.")
    cases = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            case = json.loads(line)
            missing = {"id", "query", "expected_answer", "expected_source_chunks"} - set(case)
            if missing:
                raise SystemExit(f"answer set line {line_number} missing: {sorted(missing)}")
            cases.append(case)
    if not cases:
        raise SystemExit(f"{path} is empty.")
    return cases


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
