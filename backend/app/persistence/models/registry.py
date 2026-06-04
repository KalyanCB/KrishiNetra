"""CommodityRegistry ORM model — TDS-006 §3.3 + ADR-003 (E-01-S10)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.persistence.database import Base

DEFAULT_FORECAST_HORIZONS: list[int] = [30, 60, 90]


class CommodityRegistryModel(Base):
    """Versioned operational configuration per commodity (ADR-003)."""

    __tablename__ = "commodity_registry"
    __table_args__ = (
        Index(
            "ix_registry_commodity_active",
            "commodity_id",
            unique=True,
            postgresql_where="is_active = true",
        ),
    )

    registry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_sources: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    arrival_sources: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    demand_drivers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    policy_drivers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    weather_variables: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    forecast_horizons: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: list(DEFAULT_FORECAST_HORIZONS),
    )
    required_agents: Mapped[list] = mapped_column(JSONB, nullable=False)
    optional_agents: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    signal_weights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    regime_priority: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    decision_rules: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
