"""StructuredSignal and SignalSnapshot ORM models — TDS-006 §3.8–3.9 (E-01-S05)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.persistence.database import Base

# TDS-006 §3.8: 3 years minimum for calibration — automated prune is future ops work.
STRUCTURED_SIGNAL_RETENTION_YEARS = 3


class StructuredSignalModel(Base):
    """Single agent output per run — append-only, one row per agent per day."""

    __tablename__ = "structured_signal"
    __table_args__ = (
        Index(
            "uq_signal_commodity_date_agent_registry",
            "commodity_id",
            "as_of_date",
            "agent_type",
            "registry_id",
            unique=True,
        ),
        Index("ix_signal_as_of_date", "as_of_date"),
    )

    signal_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    agent_type: Mapped[str] = mapped_column(String(32), nullable=False)
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    as_of_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    magnitude: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    signal_components: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_observation_refs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    registry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("commodity_registry.registry_id", ondelete="RESTRICT"),
        nullable=False,
    )
    agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class SignalSnapshotModel(Base):
    """Immutable daily bundle of domain signals for forecast and replay."""

    __tablename__ = "signal_snapshot"
    __table_args__ = (
        Index("ix_snapshot_commodity_as_of_date", "commodity_id", "as_of_date"),
    )

    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    registry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("commodity_registry.registry_id", ondelete="RESTRICT"),
        nullable=False,
    )
    signal_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    signals: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    trace_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data_quality_snapshot_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("data_quality_snapshot.quality_snapshot_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
