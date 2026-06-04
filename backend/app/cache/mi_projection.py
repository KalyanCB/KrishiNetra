"""Redis MI projection client — TDS-006 §4, TDS-009 §8 (E-01-S09)."""

from __future__ import annotations

import json
import logging
from datetime import date
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import redis
from redis.exceptions import RedisError

from backend.app.config.settings import get_settings

if TYPE_CHECKING:
    from redis import Redis

logger = logging.getLogger(__name__)

MI_KEY_PREFIX = "mi"
DEFAULT_MI_TTL_SECONDS = 48 * 3600


def build_mi_cache_key(commodity_id: str, as_of_date: date | str) -> str:
    """Build Redis key: ``mi:{commodity_id}:{as_of_date}`` (AC-1)."""
    date_str = as_of_date.isoformat() if isinstance(as_of_date, date) else as_of_date
    return f"{MI_KEY_PREFIX}:{commodity_id}:{date_str}"


class RedisMIProjectionClient:
    """Cache-only MI snapshot store. PostgreSQL remains source of truth (AC-4)."""

    def __init__(
        self,
        redis_client: Redis | None = None,
        *,
        redis_url: str | None = None,
        default_ttl_seconds: int = DEFAULT_MI_TTL_SECONDS,
    ) -> None:
        self._client = redis_client
        self._redis_url = redis_url
        self._default_ttl_seconds = default_ttl_seconds
        self._enabled = True

    @property
    def default_ttl_seconds(self) -> int:
        return self._default_ttl_seconds

    def _get_client(self) -> Redis | None:
        if not self._enabled:
            return None
        if self._client is not None:
            return self._client
        if self._redis_url is None:
            return None
        try:
            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            return self._client
        except (RedisError, OSError) as exc:
            logger.warning("Redis MI client unavailable: %s", exc)
            self._enabled = False
            return None

    def set_mi_snapshot(
        self,
        key: str,
        payload: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Serialize payload to JSON and store with TTL (AC-2, AC-3)."""
        client = self._get_client()
        if client is None:
            return False
        try:
            client.set(
                key,
                json.dumps(payload),
                ex=ttl if ttl is not None else self._default_ttl_seconds,
            )
            return True
        except (RedisError, OSError, TypeError, ValueError) as exc:
            logger.warning("Redis MI set failed for key %s: %s", key, exc)
            return False

    def get_mi_snapshot(self, key: str) -> dict[str, Any] | None:
        """Return cached payload or ``None`` on miss / Redis unavailable (AC-5)."""
        client = self._get_client()
        if client is None:
            return None
        try:
            raw = client.get(key)
        except (RedisError, OSError) as exc:
            logger.warning("Redis MI get failed for key %s: %s", key, exc)
            return None
        if raw is None:
            return None
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("Redis MI payload invalid JSON for key %s: %s", key, exc)
            return None
        if not isinstance(loaded, dict):
            return None
        return loaded

    def ping(self) -> bool:
        """Health probe — returns False instead of raising when Redis is down (AC-5)."""
        client = self._get_client()
        if client is None:
            return False
        try:
            return bool(client.ping())
        except (RedisError, OSError) as exc:
            logger.warning("Redis MI ping failed: %s", exc)
            return False


@lru_cache
def get_mi_projection_client() -> RedisMIProjectionClient:
    """Settings-backed singleton for app wiring."""
    settings = get_settings()
    return RedisMIProjectionClient(
        redis_url=settings.redis_url,
        default_ttl_seconds=settings.mi_cache_ttl_seconds,
    )
