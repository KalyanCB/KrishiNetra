"""Base repository and immutability guards (E-01-S02)."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from shared.persistence.contracts import block_immutable_update

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Shared CRUD helpers: get_by_id and insert."""

    def __init__(self, session: Session, model: type[T]) -> None:
        self._session = session
        self._model = model

    def get_by_id(self, entity_id: str) -> T | None:
        return self._session.get(self._model, entity_id)

    def insert(self, entity: T) -> T:
        self._session.add(entity)
        self._session.flush()
        return entity


class ImmutableVersionRepository(BaseRepository[T]):
    """
    Insert-only repository for ForecastVersion / RecommendationVersion.
    UPDATE attempts are blocked at the repository layer (ADR-002 §4).
    """

    def update(self, entity: T) -> T:
        block_immutable_update(self._model)
        return entity  # unreachable
