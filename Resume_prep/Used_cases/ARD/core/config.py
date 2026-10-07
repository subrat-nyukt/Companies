"""
ARD — core/config.py
====================
Pydantic Settings that load from .env.
Single source of truth for all configuration.
"""

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── LLM ────────────────────────────────────────────────────
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    llm_model: str = "gpt-4o"
    embed_model: str = "text-embedding-3-small"

    # ── Pinecone ────────────────────────────────────────────────
    pinecone_api_key: str = Field(..., alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field("ard-research-index", alias="PINECONE_INDEX_NAME")

    # ── RAG & Guardrail Thresholds ─────────────────────────────
    groundedness_threshold: float = Field(0.85, alias="GROUNDEDNESS_THRESHOLD")
    max_retries: int = Field(2, alias="MAX_RETRIES")
    agent_timeout_seconds: float = Field(30.0, alias="AGENT_TIMEOUT_SECONDS")
    top_k_retrieval: int = 10          # How many chunks to retrieve before RRF
    top_k_context: int = 5            # How many final chunks fed to synthesis LLM

    # ── App ─────────────────────────────────────────────────────
    log_level: str = "INFO"
    environment: str = "development"

    # ── Paths ───────────────────────────────────────────────────
    base_dir: Path = Path(__file__).resolve().parent.parent
    output_dir: Path = base_dir / "output"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


# Singleton: imported everywhere as `from core.config import settings`
settings = Settings()

# Ensure output directory exists on startup
settings.output_dir.mkdir(parents=True, exist_ok=True)
