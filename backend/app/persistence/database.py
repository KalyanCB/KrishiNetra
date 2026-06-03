"""SQLAlchemy engine, session factory, and declarative base (E-01-S01)."""

from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.config.settings import get_settings

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class Base(DeclarativeBase):
    """ORM declarative base for all persistence models."""


def create_db_engine(url: str | None = None) -> Engine:
    """Create a sync SQLAlchemy engine (psycopg2)."""
    settings = get_settings()
    return create_engine(url or settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Session factory bound to the given or default engine."""
    bound_engine = engine or create_db_engine()
    return sessionmaker(bind=bound_engine, autocommit=False, autoflush=False)


# Module-level defaults for app and Alembic env.py
engine = create_db_engine()
SessionLocal = create_session_factory(engine)


def get_session() -> Generator[Session, None, None]:
    """Yield a DB session and close it after use (non-FastAPI callers)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
