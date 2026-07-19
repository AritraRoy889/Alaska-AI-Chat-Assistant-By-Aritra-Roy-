"""
config.py – Centralised settings loader.

Reads from the .env file (or real environment variables) and exposes
a single `settings` object that the rest of the app imports.  Using
pydantic-settings means every variable is type-checked at startup.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Gemini ─────────────────────────────────────────────────────
    gemini_api_key: str
    gemini_chat_model: str = "gemini-3.5-flash"
    gemini_embedding_model: str = "models/text-embedding-004"

    # ── SQLite ─────────────────────────────────────────────────────
    database_url: str = "sqlite:///./alaska.db"

    # ── ChromaDB ───────────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"

    # ── CORS ───────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance so the .env is only parsed once."""
    return Settings()


settings = get_settings()
