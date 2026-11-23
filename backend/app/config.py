from functools import lru_cache
from pathlib import Path
from typing import Any, Self

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    domain_name: str = "GermanLawRAG"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "german_law_chunks"

    data_processed_dir: Path = Path("data/processed")

    index_chunks_path: Path = Path("data/processed/chunks.curated.jsonl")

    embedding_model: str = "BAAI/bge-m3"
    embedding_batch_size: int = 32

    embedding_device: str | None = None
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    retrieval_candidate_pool: int = 30
    # Prefer chunks whose law code and section/article match an explicit
    # reference in the query (e.g. "§ 242 StGB"). Turn off to measure plain ranking.
    exact_reference_boost: bool = True

    model_provider: str = "hosted"
    model_name: str | None = None
    model_base_url: str | None = None
    model_api_key: str | None = None
    model_temperature: float = 0.0
    model_max_tokens: int = 800
    model_timeout_seconds: float = 60.0

    # Optional separate model for the answer eval's LLM judge; unset values
    # fall back to the MODEL_* settings above.
    judge_model_name: str | None = None
    judge_model_base_url: str | None = None
    judge_model_api_key: str | None = None

    @field_validator(
        "embedding_device",
        "model_name",
        "model_base_url",
        "model_api_key",
        "judge_model_name",
        "judge_model_base_url",
        "judge_model_api_key",
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

    def judge_settings(self) -> Self:
        """Settings for the eval judge, using JUDGE_MODEL_* where set."""
        return self.model_copy(
            update={
                "model_name": self.judge_model_name or self.model_name,
                "model_base_url": self.judge_model_base_url or self.model_base_url,
                "model_api_key": self.judge_model_api_key or self.model_api_key,
            }
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
