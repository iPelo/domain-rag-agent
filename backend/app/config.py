from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    domain_name: str = "GermanLawRAG"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "german_law_chunks"

    data_raw_dir: Path = Path("data/raw")
    data_processed_dir: Path = Path("data/processed")

    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    llm_provider: str = "openai"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
