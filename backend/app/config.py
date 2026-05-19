from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    domain_name: str = "GermanLawRAG"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "german_law_chunks"

    data_raw_dir: Path = Path("data/raw/german-laws")
    data_processed_dir: Path = Path("data/processed")

    # Chunks the retrieval service loads at runtime (BM25 index + payload hydration).
    # build_index.py writes this file; defaults to the curated subset.
    index_chunks_path: Path = Path("data/processed/chunks.curated.jsonl")

    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_batch_size: int = 32
    # None lets sentence-transformers pick (MPS on Apple Silicon, else CPU).
    embedding_device: str | None = None
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    retrieval_default_top_k: int = 5
    retrieval_candidate_pool: int = 30

    llm_provider: str = "openai"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None

    @field_validator(
        "embedding_device",
        "openai_api_key",
        "anthropic_api_key",
        "langfuse_public_key",
        "langfuse_secret_key",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
