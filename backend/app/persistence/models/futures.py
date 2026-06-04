"""Futures observation ORM model — NCDEX KAPAS EOD curve facts (PI10 Track A)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.persistence.database import Base
from backend.app.persistence.models.observation import ObservationValidationStatus

FUTURES_OBSERVATION_RETENTION_YEARS = 7


class FuturesObservationSource(StrEnum):
    """Ingest source identifiers (FUTURES_SIGNAL_PROTOTYPE §5, G-04)."""

    NCDEX_PUBLIC_BHAV_PROTOTYPE = "ncdex_public_bhav_prototype"


class FuturesEnvironment(StrEnum):
    """Prototype guardrail label (FUTURES_SIGNAL_PROTOTYPE §7.3 G-01)."""

    PROTOTYPE = "prototype"
    PRODUCTION = "production"


class FuturesObservationModel(Base):
    """Append-only NCDEX KAPAS contract EOD facts for E-04 Futures agent."""

    __tablename__ = "futures_observation"
    __table_args__ = (
        Index("ix_futures_commodity_as_of_date", "commodity_id", "as_of_date"),
        Index("ix_futures_contract_as_of_date", "contract_symbol", "as_of_date"),
        Index("ix_futures_source_as_of_date", "source", "as_of_date"),
        Index("ix_futures_expiry_as_of_date", "expiry_date", "as_of_date"),
    )

    observation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    contract_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    settle_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    quote_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    settle_price_quintal: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    open_interest: Mapped[int | None] = mapped_column(Integer, nullable=True)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    provenance: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    supersedes_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    validation_status: Mapped[str] = mapped_column(
        PGEnum(
            ObservationValidationStatus,
            name="observation_validation_status",
            create_type=False,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=ObservationValidationStatus.RECEIVED.value,
    )
