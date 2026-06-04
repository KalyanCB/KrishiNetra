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
    redis_url: str = Field(
        default="redis://127.0.0.1:6379/0",
        validation_alias="REDIS_URL",
    )
    mi_cache_ttl_seconds: int = Field(
        default=48 * 3600,
        validation_alias="MI_CACHE_TTL_SECONDS",
        description="Redis MI snapshot TTL — TDS-006 §4 default 48h",
    )
    ops_api_key: str = Field(
        default="",
        validation_alias="OPS_API_KEY",
        description="Service key for internal registry ops (TDS-012 §3)",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
