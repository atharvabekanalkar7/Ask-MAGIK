"""
Application Configuration
Ask MAGIK - Phase 2: Local RAG + Llama Text-to-SQL Engine
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the ask-magik project
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    APP_NAME: str = "Ask MAGIK"
    PHASE: int = 2
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "sqlite:///./data/skyline.db"

    # Phase 2 Local AI / RAG Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:latest"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHROMA_PATH: str = "backend/rag/chroma_db"
    RAG_TOP_K: int = 4
    SQL_MAX_ROWS: int = 500
    DATA_REFRESH_NOTE: str = "Daily"

    # Fast response mode: golden-example SQL + heuristic answers (sub-second).
    # Set USE_LLM_SQL / USE_LLM_EXPLANATION to True in .env for full local LLM pipeline.
    USE_LLM_SQL: bool = False
    USE_LLM_EXPLANATION: bool = False
    LLM_TIMEOUT_SECONDS: float = 30.0

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_sqlite(self) -> bool:
        """Returns True if configured for SQLite."""
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def resolved_database_url(self) -> str:
        """
        Resolves relative SQLite database URLs to absolute filesystem paths
        relative to the ask-magik project root.
        For PostgreSQL or other production dialects, returns the URL unchanged.
        """
        if self.DATABASE_URL.startswith("sqlite:///./") or self.DATABASE_URL.startswith("sqlite:////"):
            rel_path = self.DATABASE_URL.replace("sqlite:///./", "").replace("sqlite:////", "")
            abs_path = (BASE_DIR / rel_path).resolve()
            # Ensure parent directory exists for the sqlite file
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            # Use forward slashes for SQLAlchemy SQLite URL format
            return f"sqlite:///{abs_path.as_posix()}"
        return self.DATABASE_URL

    @property
    def resolved_chroma_path(self) -> Path:
        """Resolves vector database storage directory."""
        path = (BASE_DIR / self.CHROMA_PATH).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
