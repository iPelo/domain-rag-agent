"""Grounded answer generation over retrieved source chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.generation.chat_client import ChatClient
from app.generation.prompts import GROUNDING_SYSTEM_PROMPT, build_grounded_user_prompt
from app.retrieval.models import ScoredChunk
from app.retrieval.service import RetrievalMode, RetrievalService

# This module turns retrieved sources into a final, cited answer. Flow: retrieve
# sources -> build the request text from question + sources -> ask the chat model ->
# verify every citation points to a real retrieved chunk. _CITATION_RE finds
# bracketed citations like [german-laws::gg::art-5] in the answer.
# _UNSUPPORTED_MARKER is the phrase the model uses when the sources don't support an
# answer.
_CITATION_RE = re.compile(r"\[([^\[\]]+)]")
_UNSUPPORTED_MARKER = "retrieved sources do not contain enough information"


# Signals an untrustworthy answer (it cited a chunk that wasn't retrieved,
# or cited nothing at all). The /answer route maps this to HTTP 502.
class CitationValidationError(RuntimeError):
    """Raised when an answer is not grounded in the retrieved chunks."""


# One validated citation shown to the user: the human-readable source plus its link.
@dataclass(frozen=True)
class AnswerCitation:
    chunk_id: str
    citation: str
    title: str
    source_url: str


# The full result of answering — the text, its citations, the source chunks it used,
# and the retrieval options that produced them. schemas.py converts this into JSON.
@dataclass(frozen=True)
class AnswerResult:
    query: str
    answer: str
    citations: list[AnswerCitation]
    sources: list[ScoredChunk]
    mode: str
    rerank: bool
    law_code: str | None


# Ties retrieval to the chat model: find sources, ask the model to answer using
# only those sources, then verify the citations before returning the result.
class GenerationService:
    # Both collaborators are passed in — the RetrievalService
    # (to find sources) and a ChatClient (to call the model).
    # Injecting them makes this trivial to test with fakes.
    def __init__(self, retrieval: RetrievalService, chat_client: ChatClient) -> None:
        self._retrieval = retrieval
        self._chat_client = chat_client

    # Main method. Receives the question + retrieval options; returns an
    # AnswerResult. Step 1 — retrieve the supporting source chunks. Short-circuit —
    # if nothing was retrieved, return a safe "not enough information" answer
    # WITHOUT calling the model (a model call here could not be grounded anyway).
    # Step 2 — build the request text from the question + sources and call the chat
    # model. Step 3 — validate the answer's citations against the retrieved chunks
    # before trusting it.
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


# The grounding guardrail. Reads the chunk ids the answer cited and checks them:
# - a cited id that wasn't retrieved -> raise (the model invented it).
# - no citations AND no "not enough information" note -> raise (unsupported).
# Otherwise it returns de-duplicated AnswerCitation objects in first-seen order.
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


# Pull chunk ids out of the answer text. Citations look like [id] or [id1,
# id2]; only fragments containing "::" count as ids (that's the chunk-id
# separator), so ordinary square brackets in the prose are ignored.
def _extract_chunk_ids(answer: str) -> list[str]:
    ids: list[str] = []
    for bracketed in _CITATION_RE.findall(answer):
        for part in bracketed.split(","):
            candidate = part.strip()
            if "::" in candidate:
                ids.append(candidate)
    return ids
