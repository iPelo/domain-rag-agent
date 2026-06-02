from typing import cast

from app.agent.tools import RetrievalTool
from app.retrieval.models import IndexedChunk, ScoredChunk
from app.retrieval.service import RetrievalService


class FakeRetrievalService:
    def __init__(self, results: list[ScoredChunk]) -> None:
        self.results = results
        self.calls: list[dict[str, object]] = []

    def retrieve(
        self,
        query: str,
        *,
        mode: str = "hybrid",
        top_k: int = 5,
        rerank: bool = False,
        law_code: str | None = None,
    ) -> list[ScoredChunk]:
        self.calls.append(
            {
                "query": query,
                "mode": mode,
                "top_k": top_k,
                "rerank": rerank,
                "law_code": law_code,
            }
        )
        return self.results


def test_retrieval_tool_calls_retrieval_service_with_defaults() -> None:
    result = _scored_chunk()
    fake_service = FakeRetrievalService([result])
    tool = RetrievalTool(cast(RetrievalService, fake_service))

    chunks = tool("Wo ist die Meinungsfreiheit geregelt?")

    assert fake_service.calls == [
        {
            "query": "Wo ist die Meinungsfreiheit geregelt?",
            "mode": "hybrid",
            "top_k": 5,
            "rerank": False,
            "law_code": None,
        }
    ]
    assert chunks[0].chunk_id == "german-laws::gg::art-5"
    assert chunks[0].citation == "GG Art 5"
    assert chunks[0].method == "hybrid"


def test_retrieval_tool_allows_call_level_overrides() -> None:
    fake_service = FakeRetrievalService([_scored_chunk()])
    tool = RetrievalTool(
        cast(RetrievalService, fake_service),
        default_mode="bm25",
        default_top_k=3,
        default_rerank=True,
    )

    tool("Kaufvertrag", mode="dense", top_k=2, rerank=False, law_code="BGB")

    assert fake_service.calls == [
        {
            "query": "Kaufvertrag",
            "mode": "dense",
            "top_k": 2,
            "rerank": False,
            "law_code": "BGB",
        }
    ]


def _scored_chunk() -> ScoredChunk:
    return ScoredChunk(
        chunk=IndexedChunk(
            chunk_id="german-laws::gg::art-5",
            source_id="german-laws::gg",
            title="Grundgesetz",
            text="Jeder hat das Recht, seine Meinung frei zu äußern.",
            citation="GG Art 5",
            law_code="GG",
            source_url="https://www.gesetze-im-internet.de/gg/",
        ),
        score=0.5,
        method="hybrid",
    )
