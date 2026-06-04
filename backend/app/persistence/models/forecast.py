"""Forecast, ForecastVersion, and feature store ORM — TDS-006 §3.10–3.11, §10 (E-01-S06)."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.persistence.database import Base


class ForecastStatus(StrEnum):
    """ForecastVersion run outcome — TDS-006 §3.11."""

    COMPLETE = "complete"
    FAILED = "failed"
    PARTIAL = "partial"


class ForecastModel(Base):
    """Logical forecast identity for a commodity across time."""

    __tablename__ = "forecast"

    forecast_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class FeatureSetModel(Base):
    """Feature store metadata row — TDS-006 §10; PI10 ForecastFeatureSnapshot."""

    __tablename__ = "feature_set"
    __table_args__ = (
        Index("ix_feature_set_commodity_as_of_date", "commodity_id", "as_of_date"),
        Index(
            "ix_feature_set_commodity_date_registry",
            "commodity_id",
            "as_of_date",
            "registry_id",
        ),
        Index("ix_feature_set_trace_id", "trace_id"),
    )

    feature_set_id: Mapped[UUID] = mapped_column(
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
    feature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    feature_values: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    feature_lineage: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


# PI10 Track C alias — same table as feature_set (extended @ 0013).
ForecastFeatureSnapshotModel = FeatureSetModel


class FeatureVectorModel(Base):
    """Computed feature values keyed by feature_set and name."""

    __tablename__ = "feature_vector"

    feature_set_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("feature_set.feature_set_id", ondelete="CASCADE"),
        primary_key=True,
    )
    feature_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    feature_value: Mapped[dict] = mapped_column(JSONB, nullable=False)


class ForecastVersionModel(Base):
    """Immutable versioned forecast output per as_of_date and model run."""

    __tablename__ = "forecast_version"
    __table_args__ = (
        Index(
            "uq_forecast_version_commodity_date_model_registry",
            "commodity_id",
            "as_of_date",
            "model_version",
            "registry_id",
            unique=True,
        ),
        Index("ix_forecast_version_as_of_date_published", "as_of_date", "is_published"),
        Index("ix_forecast_version_snapshot_id", "snapshot_id"),
    )

    forecast_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    forecast_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("forecast.forecast_id", ondelete="CASCADE"),
        nullable=False,
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    registry_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("commodity_registry.registry_id", ondelete="RESTRICT"),
        nullable=False,
    )
    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signal_snapshot.snapshot_id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_family: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    horizon_30: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    horizon_60: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    horizon_90: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    feature_set_ref: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("feature_set.feature_set_id", ondelete="SET NULL"),
        nullable=True,
    )
    composed_signal_refs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=ForecastStatus.COMPLETE.value,
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
