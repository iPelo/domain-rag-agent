"""Claim-level citation checks for generated answers.

A "claim" is a sentence or list item. The splitter is a heuristic tuned for
German legal prose: it does not split after common abbreviations such as
"Abs." or "Nr.", and a citation that follows a sentence's full stop is
attached to that sentence.
"""

from __future__ import annotations

import json
import re
from collections.abc import Set
from dataclasses import dataclass, field
from typing import Any

from app.generation.service import extract_chunk_ids

_ABBREVIATIONS = (
    "Abs",
    "Art",
    "Nr",
    "S",
    "Satz",
    "bzw",
    "ca",
    "d. h",
    "ggf",
    "i. V. m",
    "insb",
    "u. a",
    "usw",
    "vgl",
    "z. B",
    "z.B",
)
_PLACEHOLDER = "\u0000"
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])\s+")
_LEADING_CITATIONS_RE = re.compile(r"^((?:\[[^\[\]]*::[^\[\]]*\]\s*)+)(.*)$", re.DOTALL)
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


@dataclass(frozen=True)
class CitationCheck:
    claims: list[str]
    uncited_claims: list[str] = field(default_factory=list)
    invalid_citations: list[str] = field(default_factory=list)

    @property
    def all_claims_cited(self) -> bool:
        return bool(self.claims) and not self.uncited_claims

    @property
    def citation_coverage(self) -> float:
        if not self.claims:
            return 0.0
        return 1.0 - len(self.uncited_claims) / len(self.claims)


def split_claims(answer: str) -> list[str]:
    """Split an answer into sentence or list-item claims."""
    protected = answer
    for abbreviation in _ABBREVIATIONS:
        protected = protected.replace(f"{abbreviation}.", f"{abbreviation}{_PLACEHOLDER}")

    claims: list[str] = []
    for line in protected.splitlines():
        line = _LIST_MARKER_RE.sub("", line).strip()
        if not line:
            continue
        for fragment in _SENTENCE_END_RE.split(line):
            fragment = fragment.strip()
            if not fragment:
                continue
            match = _LEADING_CITATIONS_RE.match(fragment)
            if match and claims:
                claims[-1] = f"{claims[-1]} {match.group(1).strip()}"
                fragment = match.group(2).strip()
                if not fragment:
                    continue
            claims.append(fragment)

    restored = [claim.replace(_PLACEHOLDER, ".") for claim in claims]
    return [claim for claim in restored if _is_claim(claim)]


def check_citations(answer: str, allowed_chunk_ids: Set[str]) -> CitationCheck:
    """Check that every claim cites at least one chunk, and only allowed chunks."""
    claims = split_claims(answer)
    uncited = [claim for claim in claims if not extract_chunk_ids(claim)]
    invalid = sorted({cid for cid in extract_chunk_ids(answer) if cid not in allowed_chunk_ids})
    return CitationCheck(claims=claims, uncited_claims=uncited, invalid_citations=invalid)


def _is_claim(text: str) -> bool:
    # Headings that introduce a list ("Die Voraussetzungen sind:") state nothing
    # on their own, and fragments without letters are leftovers.
    without_citations = re.sub(r"\[[^\[\]]*\]", "", text).strip()
    if not any(char.isalpha() for char in without_citations):
        return False
    return not without_citations.endswith(":")


JUDGE_SYSTEM_PROMPT = """You grade answers about German federal law.

Compare the candidate answer with the reference answer and the cited source texts.
Return only a JSON object: {"score": <integer 1-5>, "reason": "<one sentence>"}.
5 = every statement is supported by the sources and agrees with the reference.
3 = mostly correct, but something is missing or loosely supported.
1 = contradicts the reference or the sources, or is unsupported.
"""


def build_judge_prompt(*, query: str, expected_answer: str, answer: str, sources: list[str]) -> str:
    source_text = "\n\n".join(sources) if sources else "(no sources cited)"
    return (
        f"Question:\n{query}\n\nReference answer:\n{expected_answer}\n\n"
        f"Candidate answer:\n{answer}\n\nCited sources:\n{source_text}"
    )


def parse_judge_response(raw: str) -> dict[str, Any]:
    """Extract `{"score", "reason"}` from a judge reply; score is None if unreadable."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict):
            score = data.get("score")
            if isinstance(score, int | float) and 1 <= score <= 5:
                return {"score": int(score), "reason": str(data.get("reason", ""))}
    return {"score": None, "reason": f"Unparseable judge reply: {raw[:200]}"}
