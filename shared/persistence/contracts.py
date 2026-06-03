"""Repository and immutability contracts (E-01-S02, TDS-006 §6–§8)."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class RepositoryProtocol(Protocol[T]):
    """Minimal repository surface for versioned and reference entities."""

    def get_by_id(self, entity_id: str) -> T | None: ...

    def insert(self, entity: T) -> T: ...


class AppendOnlyRepositoryProtocol(RepositoryProtocol[T], Protocol):
    """Observations and other append-only facts — insert only, no UPDATE."""

    def insert(self, entity: T) -> T: ...


class ImmutableVersionRepositoryProtocol(RepositoryProtocol[T], Protocol):
    """
    ForecastVersion, RecommendationVersion — insert-only at repository layer.
    Published numeric fields must never be updated in place (TDS-006 §6).
    """

    def insert(self, entity: T) -> T: ...

    def update(self, entity: T) -> T: ...  # noqa: D102 — intentionally restricted


class VersionedConfigRepositoryProtocol(RepositoryProtocol[T], Protocol):
    """CommodityRegistry — versioned config; activation swap, not in-place mutation."""

    def get_active(self, commodity_id: str) -> T | None: ...


def block_immutable_update(entity_type: type[Any]) -> None:
    """Raise when callers attempt in-place UPDATE on immutable version rows."""
    msg = (
        f"UPDATE blocked for immutable version entity {entity_type.__name__} "
        "(TDS-006 §6; use insert-only versioning)"
    )
    raise ImmutableVersionUpdateError(msg)


class ImmutableVersionUpdateError(RuntimeError):
    """Raised when repository layer blocks UPDATE on immutable version tables."""
