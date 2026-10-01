from typing import cast

import pytest
from app.generation.service import CitationValidationError, GenerationService
from app.retrieval.models import IndexedChunk, ScoredChunk
from app.retrieval.service import RetrievalService


class FakeChatClient:
    def __init__(self, answer: str) -> None:
        self.answer = answer
        self.system_prompt = ""
        self.user_prompt = ""
        self.calls = 0

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        self.calls += 1
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return self.answer


class FakeRetrievalService:
    def __init__(self, sources: list[ScoredChunk]) -> None:
        self.sources = sources
        self.query = ""
        self.top_k = 0

    def retrieve(
        self,
        query: str,
        *,
        mode: str = "hybrid",
        top_k: int = 5,
        rerank: bool = False,
        law_code: str | None = None,
    ) -> list[ScoredChunk]:
        self.query = query
        self.top_k = top_k
        return self.sources


def test_generation_builds_grounded_answer_with_citations() -> None:
    source = _scored_chunk("german-laws::gg::art-5", "Meinungsfreiheit steht in Art 5 GG.")
    chat = FakeChatClient("Die Meinungsfreiheit ist geregelt. [german-laws::gg::art-5]")
    retrieval = FakeRetrievalService([source])
    service = GenerationService(cast(RetrievalService, retrieval), chat)

    result = service.answer("Wo ist die Meinungsfreiheit geregelt?", top_k=3)

    assert retrieval.query == "Wo ist die Meinungsfreiheit geregelt?"
    assert retrieval.top_k == 3
    assert chat.calls == 1
    assert "chunk_id: german-laws::gg::art-5" in chat.user_prompt
    assert "Meinungsfreiheit steht in Art 5 GG." in chat.user_prompt
    assert result.answer == "Die Meinungsfreiheit ist geregelt. [german-laws::gg::art-5]"
    assert result.citations[0].chunk_id == "german-laws::gg::art-5"
    assert result.sources == [source]


def test_generation_without_sources_returns_unsupported_answer_without_model_call() -> None:
    chat = FakeChatClient("should not be used")
    retrieval = FakeRetrievalService([])
    service = GenerationService(cast(RetrievalService, retrieval), chat)

    result = service.answer("Nicht im Korpus?")

    assert chat.calls == 0
    assert result.citations == []
    assert result.sources == []
    assert "not contain enough information" in result.answer


def test_generation_rejects_answers_without_citations() -> None:
    source = _scored_chunk("german-laws::bgb::sec-433", "Der Verkäufer muss liefern.")
    chat = FakeChatClient("Der Verkäufer muss die Sache übergeben.")
    service = GenerationService(cast(RetrievalService, FakeRetrievalService([source])), chat)

    with pytest.raises(CitationValidationError):
        service.answer("Welche Pflichten hat der Verkäufer?")


def test_generation_rejects_unknown_chunk_citations() -> None:
    source = _scored_chunk("german-laws::bgb::sec-433", "Der Verkäufer muss liefern.")
    chat = FakeChatClient("Der Verkäufer muss liefern. [german-laws::bgb::sec-999]")
    service = GenerationService(cast(RetrievalService, FakeRetrievalService([source])), chat)

    with pytest.raises(CitationValidationError):
        service.answer("Welche Pflichten hat der Verkäufer?")


def _scored_chunk(chunk_id: str, text: str) -> ScoredChunk:
    return ScoredChunk(
        chunk=IndexedChunk(
            chunk_id=chunk_id,
            source_id="german-laws::test",
            title="Test Law",
            text=text,
            citation="GG Art 5",
            law_code="GG",
            source_url="https://example.test/",
        ),
        score=1.0,
        method="hybrid",
    )
