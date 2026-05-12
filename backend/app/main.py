from fastapi import Depends, FastAPI

from app.config import Settings, get_settings

app = FastAPI(
    title="GermanLawRAG API",
    description="Retrieval-augmented assistant for German legal texts.",
    version="0.1.0",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "GermanLawRAG API"}


@app.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "status": "ok",
        "domain": settings.domain_name,
        "environment": settings.app_env,
        "qdrant_collection": settings.qdrant_collection,
    }
