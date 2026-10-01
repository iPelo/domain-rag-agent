"""Grounded answer generation over retrieved source chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.generation.chat_client import ChatClient
from app.generation.prompts import GROUNDING_SYSTEM_PROMPT, build_grounded_user_prompt
from app.retrieval.models import ScoredChunk
from app.retrieval.service import RetrievalMode, RetrievalService

_CITATION_RE = re.compile(r"\[([^\[\]]+)]")
_UNSUPPORTED_MARKER = "retrieved sources do not contain enough information"


class CitationValidationError(RuntimeError):
    """Raised when an answer is not grounded in the retrieved chunks."""


@dataclass(frozen=True)
class AnswerCitation:
    chunk_id: str
    citation: str
    title: str
    source_url: str


@dataclass(frozen=True)
class AnswerResult:
    query: str
    answer: str
    citations: list[AnswerCitation]
    sources: list[ScoredChunk]
    mode: str
    rerank: bool
    law_code: str | None


class GenerationService:
    def __init__(self, retrieval: RetrievalService, chat_client: ChatClient) -> None:
        self._retrieval = retrieval
        self._chat_client = chat_client

    def answer(
        self,
        query: str,
        *,
        mode: RetrievalMode = "hybrid",
        top_k: int = 5,
        rerank: bool = False,
        law_code: str | None = None,
    ) -> AnswerResult:
        sources = self._retrieval.retrieve(
            query,
            mode=mode,
            top_k=top_k,
            rerank=rerank,
            law_code=law_code,
        )
        if not sources:
            return AnswerResult(
                query=query,
                answer="The retrieved sources do not contain enough information to answer.",
                citations=[],
                sources=[],
                mode=mode,
                rerank=rerank,
                law_code=law_code,
            )

        user_prompt = build_grounded_user_prompt(query, sources)
        answer = self._chat_client.complete(
            system_prompt=GROUNDING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        citations = _citations_for_answer(answer, sources)
        return AnswerResult(
            query=query,
            answer=answer,
            citations=citations,
            sources=sources,
            mode=mode,
            rerank=rerank,
            law_code=law_code,
        )


def _citations_for_answer(answer: str, sources: list[ScoredChunk]) -> list[AnswerCitation]:
    allowed = {source.chunk.chunk_id: source.chunk for source in sources}
    cited_ids = _extract_chunk_ids(answer)
    unsupported = _UNSUPPORTED_MARKER in answer.casefold()

    invalid = sorted(cited_id for cited_id in cited_ids if cited_id not in allowed)
    if invalid:
        raise CitationValidationError(f"Answer cited unknown chunk ids: {', '.join(invalid)}")
    if not cited_ids and not unsupported:
        raise CitationValidationError("Answer did not cite any retrieved chunk ids.")

    citations: list[AnswerCitation] = []
    seen: set[str] = set()
    for cited_id in cited_ids:
        if cited_id in seen:
            continue
        seen.add(cited_id)
        chunk = allowed[cited_id]
        citations.append(
            AnswerCitation(
                chunk_id=chunk.chunk_id,
                citation=chunk.citation,
                title=chunk.title,
                source_url=chunk.source_url,
            )
        )
    return citations


def _extract_chunk_ids(answer: str) -> list[str]:
    ids: list[str] = []
    for bracketed in _CITATION_RE.findall(answer):
        for part in bracketed.split(","):
            candidate = part.strip()
            if "::" in candidate:
                ids.append(candidate)
    return ids
