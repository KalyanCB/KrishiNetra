"""Application settings (E-01-S01/S02). DATABASE_URL from environment."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql://krishinetra:krishinetra@127.0.0.1:5432/krishinetra",
        validation_alias="DATABASE_URL",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
