"""Policy observation ORM model — structured government/policy events (PI10 Track B)."""

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

POLICY_OBSERVATION_RETENTION_YEARS = 10


class PolicyType(StrEnum):
    """Policy event categories aligned to SIGNAL_ENGINE_V1 §5 (Policy agent inputs)."""

    MSP_ANNOUNCEMENT = "msp_announcement"
    CCI_PROCUREMENT = "cci_procurement"
    EXPORT_BAN = "export_ban"
    EXPORT_RESTRICTION_LIFTED = "export_restriction_lifted"


class PolicyObservationSource(StrEnum):
    """Ingest source identifiers — manual entry, PIB/CCI stubs, seed fixtures."""

    PIB_MANUAL = "pib_manual"
    CCI_MANUAL = "cci_manual"
    SEED_FIXTURE = "seed_fixture"


class PolicyObservationModel(Base):
    """Append-only policy facts for E-03 ingest (not structured_signal)."""

    __tablename__ = "policy_observation"
    __table_args__ = (
        Index("ix_policy_commodity_effective_date", "commodity_id", "effective_date"),
        Index("ix_policy_type_effective_date", "policy_type", "effective_date"),
        Index("ix_policy_source_published_date", "source", "published_date"),
    )

    observation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    published_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    impact_direction: Mapped[str] = mapped_column(String(16), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
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
