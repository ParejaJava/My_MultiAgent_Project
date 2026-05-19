"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


def resolve_project_path(path: Path | str) -> Path:
    """Resolve a path relative to the project root unless it is already absolute."""
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def project_relative_source(path: Path | str) -> str:
    """Return a stable POSIX source path without embedding the local checkout path."""
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return candidate.as_posix()


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the application."""

    app_name: str = os.getenv("APP_NAME", "Operations Diagnosis Copilot")
    app_env: str = os.getenv("APP_ENV", "local")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4.1-mini")
    rag_config_path: str = os.getenv("RAG_CONFIG_PATH", "configs/rag/bge_local.yaml")
    vector_store_path: str = os.getenv("VECTOR_STORE_PATH", "D:/AgentData/VectorStore")
    bm25_index_path: str = os.getenv("BM25_INDEX_PATH", "D:/AgentData/BM25Store")
    model_cache_path: str = os.getenv("MODEL_CACHE_PATH", "D:/AgentData/ModelCache")
    jieba_user_dict_path: str = os.getenv("JIEBA_USER_DICT_PATH", "configs/jieba/userdict.txt")


settings = Settings()
