"""Price and arrival observation ORM models — TDS-006 §3.6–3.7 (E-01-S04)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.persistence.database import Base

# TDS-006 §3.6: 7 years hot retention — automated prune is future ops work.
OBSERVATION_RETENTION_YEARS = 7


class ObservationValidationStatus(StrEnum):
    """Append-only observation lifecycle (E-01-S04 AC-5, PI8 Track A)."""

    RECEIVED = "received"  # draft / pending QA
    VALIDATED = "validated"
    PUBLISHED = "published"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


# Alias for PI8 workflow docs: received == draft pending validation.
DRAFT_VALIDATION_STATUS = ObservationValidationStatus.RECEIVED


_validation_status_enum = PGEnum(
    ObservationValidationStatus,
    name="observation_validation_status",
    create_type=False,
    values_callable=lambda enum: [member.value for member in enum],
)


class PriceObservationModel(Base):
    """Append-only mandi price facts (TDS-006 §3.6)."""

    __tablename__ = "price_observation"
    __table_args__ = (
        Index("ix_price_commodity_as_of_date", "commodity_id", "as_of_date"),
        Index("ix_price_market_observed_at", "market_id", "observed_at"),
        Index("ix_price_source_as_of_date", "source", "as_of_date"),
    )

    observation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    market_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("market.market_id", ondelete="RESTRICT"),
        nullable=False,
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    price_type: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    quality_grade: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supersedes_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    validation_status: Mapped[str] = mapped_column(
        _validation_status_enum,
        nullable=False,
        default=ObservationValidationStatus.RECEIVED.value,
    )


class ArrivalObservationModel(Base):
    """Append-only arrival volume facts (TDS-006 §3.7)."""

    __tablename__ = "arrival_observation"
    __table_args__ = (
        Index("ix_arrival_commodity_as_of_date", "commodity_id", "as_of_date"),
        Index("ix_arrival_market_observed_at", "market_id", "observed_at"),
    )

    observation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    market_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("market.market_id", ondelete="RESTRICT"),
        nullable=False,
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    volume: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    supersedes_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    validation_status: Mapped[str] = mapped_column(
        _validation_status_enum,
        nullable=False,
        default=ObservationValidationStatus.RECEIVED.value,
    )
