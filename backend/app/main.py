from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query

from app.config import Settings, get_settings
from app.generation.chat_client import (
    ModelConfigurationError,
    ModelRequestError,
    build_chat_client,
)
from app.generation.service import CitationValidationError, GenerationService
from app.retrieval.service import (
    RETRIEVAL_MODES,
    RetrievalMode,
    RetrievalService,
    get_retrieval_service,
)
from app.schemas import (
    AnswerRequest,
    AnswerResponse,
    IndexStatsResponse,
    RetrievedChunk,
    RetrieveResponse,
)

app = FastAPI(
    title="GermanLawRAG API",
    description="Retrieval service for German legal texts.",
    version="0.1.0",
)


def retrieval_service() -> RetrievalService:
    """Dependency: the retrieval singleton, or a clean 503 if the index is missing."""
    try:
        return get_retrieval_service()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Retrieval index not ready ({exc}). Run `make index` to build it.",
        ) from exc


SettingsDep = Annotated[Settings, Depends(get_settings)]
RetrievalServiceDep = Annotated[RetrievalService, Depends(retrieval_service)]
QueryText = Annotated[
    str,
    Query(min_length=2, description="Natural-language legal query."),
]
ModeQuery = Annotated[
    RetrievalMode,
    Query(description=f"Retrieval strategy: one of {', '.join(RETRIEVAL_MODES)}."),
]
TopKQuery = Annotated[
    int,
    Query(ge=1, le=50, description="Number of chunks to return."),
]
RerankQuery = Annotated[
    bool,
    Query(description="Re-score a wider candidate pool with the cross-encoder."),
]
LawCodeQuery = Annotated[
    str | None,
    Query(description="Restrict to one law, e.g. 'BGB' or 'GG' (exact match)."),
]


def generation_service(
    settings: SettingsDep,
    service: RetrievalServiceDep,
) -> GenerationService:
    try:
        chat_client = build_chat_client(settings)
    except ModelConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return GenerationService(service, chat_client)


GenerationServiceDep = Annotated[GenerationService, Depends(generation_service)]


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "GermanLawRAG API"}


@app.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {
        "status": "ok",
        "domain": settings.domain_name,
        "environment": settings.app_env,
        "qdrant_collection": settings.qdrant_collection,
    }


@app.get("/index/stats", response_model=IndexStatsResponse)
def index_stats(
    service: RetrievalServiceDep,
) -> IndexStatsResponse:
    try:
        return IndexStatsResponse.from_stats(service.stats())
    except Exception as exc:  # Qdrant unreachable
        raise HTTPException(status_code=503, detail=f"Qdrant unavailable: {exc}") from exc


@app.get("/retrieve", response_model=RetrieveResponse)
def retrieve(
    service: RetrievalServiceDep,
    q: QueryText,
    mode: ModeQuery = "hybrid",
    top_k: TopKQuery = 5,
    rerank: RerankQuery = False,
    law_code: LawCodeQuery = None,
) -> RetrieveResponse:
    try:
        scored = service.retrieve(q, mode=mode, top_k=top_k, rerank=rerank, law_code=law_code)
    except Exception as exc:  # Qdrant unreachable, model load failure, etc.
        raise HTTPException(status_code=503, detail=f"Retrieval failed: {exc}") from exc

    return RetrieveResponse(
        query=q,
        mode=mode,
        rerank=rerank,
        law_code=law_code,
        count=len(scored),
        results=[RetrievedChunk.from_scored_chunk(item) for item in scored],
    )


@app.post("/answer", response_model=AnswerResponse)
def answer(
    request: AnswerRequest,
    service: GenerationServiceDep,
) -> AnswerResponse:
    try:
        result = service.answer(
            request.query,
            mode=request.mode,
            top_k=request.top_k,
            rerank=request.rerank,
            law_code=request.law_code,
        )
    except CitationValidationError as exc:
        raise HTTPException(
            status_code=502, detail=f"Generated answer is not grounded: {exc}"
        ) from exc
    except ModelRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnswerResponse.from_result(result)
