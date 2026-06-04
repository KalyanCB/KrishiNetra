"""OGD Data API client for Agmarknet mandi prices (E-03-S01 production)."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx

from backend.app.services.ingest.agmarknet.constants import (
    DEFAULT_OGD_FORMAT,
    DEFAULT_OGD_PAGE_LIMIT,
    OGD_API_BASE_URL,
    OGD_RESOURCE_UUID,
)

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class OgdApiError(RuntimeError):
    """Raised when the OGD API returns an error envelope or fails after retries."""


@dataclass(frozen=True, slots=True)
class OgdPage:
    """One paginated OGD response page."""

    payload: dict[str, Any]
    offset: int
    limit: int
    total: int
    record_count: int


@dataclass(frozen=True, slots=True)
class OgdClientConfig:
    """HTTP client configuration for OGD Agmarknet pulls."""

    api_key: str
    resource_uuid: str = OGD_RESOURCE_UUID
    base_url: str = OGD_API_BASE_URL
    page_limit: int = DEFAULT_OGD_PAGE_LIMIT
    response_format: str = DEFAULT_OGD_FORMAT
    timeout_seconds: float = 30.0
    max_retries: int = 5
    backoff_base_seconds: float = 1.0


class OgdAgmarknetClient:
    """Fetch Agmarknet mandi rows from api.data.gov.in with pagination and retries."""

    def __init__(
        self,
        config: OgdClientConfig,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        if not config.api_key.strip():
            msg = "OGD API key is required"
            raise ValueError(msg)
        self._config = config
        self._client = client
        self._resource_url = f"{config.base_url.rstrip('/')}/{config.resource_uuid}"

    def fetch_page(
        self,
        *,
        offset: int = 0,
        limit: int | None = None,
        filters: dict[str, str] | None = None,
    ) -> OgdPage:
        """Fetch a single OGD page."""
        page_limit = limit if limit is not None else self._config.page_limit
        params = _build_query_params(
            api_key=self._config.api_key,
            offset=offset,
            limit=page_limit,
            response_format=self._config.response_format,
            filters=filters,
        )
        payload = self._request_with_retries(params)
        _raise_on_ogd_error(payload)
        total = _coerce_int(payload.get("total"), default=0)
        records = payload.get("records")
        record_count = len(records) if isinstance(records, list) else 0
        return OgdPage(
            payload=payload,
            offset=offset,
            limit=page_limit,
            total=total,
            record_count=record_count,
        )

    def iter_pages(
        self,
        *,
        filters: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> Iterator[OgdPage]:
        """Yield OGD pages until offset reaches total or a page returns no records."""
        page_limit = limit if limit is not None else self._config.page_limit
        offset = 0
        while True:
            page = self.fetch_page(offset=offset, limit=page_limit, filters=filters)
            yield page
            if page.record_count == 0:
                break
            offset += page.limit
            if page.total > 0 and offset >= page.total:
                break
            if page.total == 0 and page.record_count < page.limit:
                break

    def fetch_all(
        self,
        *,
        filters: dict[str, str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch and concatenate all record dicts across pages."""
        rows: list[dict[str, Any]] = []
        for page in self.iter_pages(filters=filters, limit=limit):
            records = page.payload.get("records")
            if isinstance(records, list):
                for item in records:
                    if isinstance(item, dict):
                        rows.append(item)
        return rows

    def _request_with_retries(self, params: dict[str, str | int]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._config.max_retries):
            try:
                response = self._get(params)
                if response.status_code in RETRYABLE_STATUS_CODES:
                    msg = f"OGD HTTP {response.status_code}"
                    raise OgdApiError(msg)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    msg = "OGD response must be a JSON object"
                    raise OgdApiError(msg)
                return payload
            except (httpx.HTTPError, OgdApiError) as exc:
                last_error = exc
                if attempt >= self._config.max_retries - 1:
                    break
                delay = self._config.backoff_base_seconds * (2**attempt)
                logger.warning(
                    "OGD request failed (attempt %s/%s), retry in %.1fs: %s",
                    attempt + 1,
                    self._config.max_retries,
                    delay,
                    exc,
                )
                time.sleep(delay)
        msg = f"OGD request failed after {self._config.max_retries} attempts"
        raise OgdApiError(msg) from last_error

    def _get(self, params: dict[str, str | int]) -> httpx.Response:
        if self._client is not None:
            return self._client.get(self._resource_url, params=params)
        with httpx.Client(timeout=self._config.timeout_seconds) as client:
            return client.get(self._resource_url, params=params)


def _build_query_params(
    *,
    api_key: str,
    offset: int,
    limit: int,
    response_format: str,
    filters: dict[str, str] | None,
) -> dict[str, str | int]:
    params: dict[str, str | int] = {
        "api-key": api_key,
        "format": response_format,
        "limit": limit,
        "offset": offset,
    }
    if filters:
        for key, value in filters.items():
            params[f"filters[{key}]"] = value
    return params


def _raise_on_ogd_error(payload: dict[str, Any]) -> None:
    error = payload.get("error")
    if error is None:
        return
    if isinstance(error, dict):
        message = str(error.get("message") or error)
    else:
        message = str(error)
    raise OgdApiError(message)


def _coerce_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
