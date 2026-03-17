from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    model_provider: Literal["openai"] = "openai"
    langsmith_api_key: str | None = None
    langsmith_project: str = "ai-due-diligence"
    langsmith_tracing: bool = True
    chroma_persist_dir: Path = Path("./data/chroma")
    upload_dir: Path = Path("./data/uploads")
    sqlite_database_path: Path = Path("./data/app.db")
    sqlite_checkpoint_path: Path = Path("./data/langgraph_checkpoints.db")
    max_file_size_bytes: int = 50 * 1024 * 1024
    max_files_per_analysis: int = 25
    max_combined_size_bytes: int = 250 * 1024 * 1024
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_retrieval: int = 6
    deepening_retry_limit: int = 2
    frontend_origin: str = Field(default="http://localhost:3000")
    tavily_api_key: str | None = None


settings = Settings()


def ensure_directories() -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_database_path.parent.mkdir(parents=True, exist_ok=True)
