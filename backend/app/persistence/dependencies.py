"""FastAPI database dependencies (E-01-S02)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from backend.app.persistence.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Request-scoped session; commit/rollback owned by route or UoW."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
