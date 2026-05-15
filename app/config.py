"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the application."""

    app_name: str = os.getenv("APP_NAME", "Operations Diagnosis Copilot")
    app_env: str = os.getenv("APP_ENV", "local")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    vector_store_path: str = os.getenv("VECTOR_STORE_PATH", "data/vector_store")


settings = Settings()
