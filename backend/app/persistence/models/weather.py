"""Weather observation ORM model — regional/district daily meteorology (PI6 Track C)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.persistence.database import Base
from backend.app.persistence.models.observation import ObservationValidationStatus

# Align with price/arrival hot retention; automated prune is future ops work.
WEATHER_OBSERVATION_RETENTION_YEARS = 7


class WeatherObservationSource(StrEnum):
    """Ingest source identifiers (WEATHER_DATA_STRATEGY_V1 tiering)."""

    NASA_POWER = "nasa_power"
    IMD = "imd"


class WeatherObservationModel(Base):
    """Append-only district/regional weather facts for E-03 ingest (not structured_signal)."""

    __tablename__ = "weather_observation"
    __table_args__ = (
        Index("ix_weather_region_as_of_date", "region_id", "as_of_date"),
        Index("ix_weather_commodity_as_of_date", "commodity_id", "as_of_date"),
        Index("ix_weather_source_as_of_date", "source", "as_of_date"),
    )

    observation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    region_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("region.region_id", ondelete="RESTRICT"),
        nullable=False,
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    district_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rainfall_mm: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    temperature_min_c: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    temperature_max_c: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    temperature_mean_c: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    relative_humidity_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
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
