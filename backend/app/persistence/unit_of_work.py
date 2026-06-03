"""Unit of Work transaction boundary (E-01-S02)."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session

from backend.app.persistence.database import SessionLocal
from backend.app.persistence.repositories.reference import CommodityRepository


class UnitOfWork:
    """Coordinates a single transaction across repositories."""

    def __init__(self, session: Session | None = None) -> None:
        self._owns_session = session is None
        self.session = session or SessionLocal()
        self.commodities = CommodityRepository(self.session)

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        if self._owns_session:
            self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
