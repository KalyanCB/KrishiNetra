"""DataQualitySnapshot ORM model — TDS-006 §3.17 (E-01-S08)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.persistence.database import Base

# TDS-006 §3.17: 2 years hot retention — automated prune is future ops work.
DATA_QUALITY_RETENTION_YEARS = 2


class DataQualitySnapshotModel(Base):
    """Per-refresh source health for trust and confidence adjustment."""

    __tablename__ = "data_quality_snapshot"
    __table_args__ = (
        Index("ix_quality_commodity_as_of_date", "commodity_id", "as_of_date"),
    )

    quality_snapshot_id: Mapped[UUID] = mapped_column(
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
    source_health: Mapped[dict] = mapped_column(JSONB, nullable=False)
    overall_quality_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    agmarknet_lag_hours: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )
    futures_feed_ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    signals_missing: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    confidence_penalty_factor: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("0"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    commodity: Mapped[object] = relationship()
    commodity_registry: Mapped[object] = relationship(
        "CommodityRegistryModel",
        foreign_keys=[registry_id],
    )
