import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    # Azure OpenAI
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_api_version: str = "2024-02-01"
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # Azure AI Search
    azure_search_endpoint: str
    azure_search_key: str
    azure_search_index: str = "kyc-index"

    # Azure AI Document Intelligence (Form Recognizer)
    azure_doc_intel_endpoint: str
    azure_doc_intel_key: str

    # Azure AI Vision
    azure_vision_endpoint: str
    azure_vision_key: str

    # Application
    env: str = "development"
    log_level: str = "INFO"

    # Confidence threshold: above this → auto-approve, below → HITL queue
    confidence_threshold: float = 0.80

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
