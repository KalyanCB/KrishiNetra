"""Forecast quality metric persistence — PI11 Track D (TDS-000, TDS-011)."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.persistence.database import Base


class ForecastQualityMetricModel(Base):
    """Persisted backtest KPIs per commodity, date, registry, and horizon."""

    __tablename__ = "forecast_quality_metric"
    __table_args__ = (
        Index(
            "uq_forecast_quality_commodity_date_registry_horizon",
            "commodity_id",
            "as_of_date",
            "registry_id",
            "horizon_days",
            "model_version",
            "assessment_source",
            unique=True,
        ),
        Index(
            "ix_forecast_quality_commodity_as_of_date",
            "commodity_id",
            "as_of_date",
        ),
    )

    forecast_quality_id: Mapped[UUID] = mapped_column(
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
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    forecast_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    assessment_source: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="backtest",
    )
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    mae: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    rmse: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    mape: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    coverage: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    metrics_detail: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
