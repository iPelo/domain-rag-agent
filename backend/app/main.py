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

# This module is the web entry point — it defines the FastAPI app and every HTTP
# route the frontend (or curl) can call. Each route stays thin: validate input,
# call a service, then convert the result into a response model from schemas.py.
# The heavy lifting lives in app/retrieval (search) and app/generation (answering).
# `app` is the ASGI application uvicorn serves (see `uvicorn app.main:app`).
app = FastAPI(
    title="GermanLawRAG API",
    description="Retrieval service for German legal texts.",
    version="0.1.0",
)


# A FastAPI "dependency" — a function whose return value is injected
# into any route that asks for it (see RetrievalServiceDep below). It
# hands routes the shared search service, built once and reused. Error
# handling: a missing index file or unreachable store is turned into a
# clean HTTP 503 with a fix-it hint, instead of leaking a raw 500.
def retrieval_service() -> RetrievalService:
    """Dependency: the retrieval singleton, or a clean 503 if the index is missing."""
    try:
        return get_retrieval_service()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Retrieval index not ready ({exc}). Run `make index` to build it.",
        ) from exc


# These Annotated aliases pair a type with FastAPI metadata — Depends(...) for
# dependency injection, Query(...) for input validation and the auto-built API docs.
# Reusing them keeps the route signatures below short, and the rules are enforced
# automatically (e.g. TopKQuery rejects values outside 1..50 with HTTP 422).
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


# Dependency that builds the answer service on demand. It needs
# settings (for chat-model configuration) and the retrieval service (to
# find sources to cite). If the chat model is not configured in .env it
# returns 503, so /retrieve keeps working even when /answer cannot.
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


# Liveness check. Cheap on purpose: it never builds the index or loads a
# model, so it answers instantly and is safe to hit from uptime probes.
@app.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {
        "status": "ok",
        "domain": settings.domain_name,
        "environment": settings.app_env,
        "qdrant_collection": settings.qdrant_collection,
    }


# Reports index health — how many chunks are loaded and how many vectors Qdrant
# holds. The broad `except` turns any Qdrant transport failure into a 503.
@app.get("/index/stats", response_model=IndexStatsResponse)
def index_stats(
    service: RetrievalServiceDep,
) -> IndexStatsResponse:
    try:
        return IndexStatsResponse.from_stats(service.stats())
    except Exception as exc:  # Qdrant unreachable
        raise HTTPException(status_code=503, detail=f"Qdrant unavailable: {exc}") from exc


# Search endpoint (GET). Receives the query + options as URL params and
# returns ranked source chunks — no chat model involved, so it works without
# model config. Flow: service.retrieve(...) -> wrap each ScoredChunk as a
# RetrievedChunk response -> FastAPI serializes the RetrieveResponse to JSON.
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


# Answer endpoint (POST). Uses a JSON body (AnswerRequest) because it carries
# more options and triggers the chat model to write a cited answer over the
# sources. Two failures map to HTTP 502: the answer isn't grounded in the sources
# (CitationValidationError) or the model call itself fails (ModelRequestError).
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
            status_code=502, detail=f"Answer is not grounded: {exc}"
        ) from exc
    except ModelRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return AnswerResponse.from_result(result)
