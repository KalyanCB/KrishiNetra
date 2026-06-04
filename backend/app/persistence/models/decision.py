"""Decision session stack ORM — TDS-006 §3.12–3.16 (E-01-S07)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.persistence.database import Base

# TDS-006 §3.12–3.13: 5 years minimum retention — automated prune is future ops work.
DECISION_RETENTION_YEARS = 5


class OutcomeValidationStatus(StrEnum):
    """Outcome calibration lifecycle — TDS-006 §3.16, story AC-5."""

    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"


class UserContextModel(Base):
    """Immutable position-level inputs for one decision session."""

    __tablename__ = "user_context"
    __table_args__ = (
        Index("ix_user_context_persona_captured_at", "persona_type", "captured_at"),
    )

    context_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    storage_access: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
    )
    liquidity_need: Mapped[str] = mapped_column(String(16), nullable=False)
    financing_profile: Mapped[dict] = mapped_column(JSONB, nullable=False)
    risk_profile: Mapped[dict] = mapped_column(JSONB, nullable=False)
    persona_type: Mapped[str] = mapped_column(String(16), nullable=False)
    region_preference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    position_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class DecisionSessionModel(Base):
    """Audit root binding context, MI, recommendation, and explanation ref."""

    __tablename__ = "decision_session"
    __table_args__ = (
        Index("ix_decision_session_commodity_as_of_date", "commodity_id", "as_of_date"),
        Index("ix_decision_session_context_id", "context_id"),
        Index("ix_decision_session_status_created_at", "status", "created_at"),
    )

    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        server_default=func.now(),
    )
    context_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("user_context.context_id", ondelete="RESTRICT"),
        nullable=False,
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
    forecast_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )
    snapshot_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("signal_snapshot.snapshot_id", ondelete="RESTRICT"),
        nullable=False,
    )
    mi_snapshot_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    recommendation_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recommendation.recommendation_id", ondelete="SET NULL"),
        nullable=True,
    )
    explanation_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
    )
    persona_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="pending",
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class RecommendationModel(Base):
    """Session-scoped logical recommendation identity."""

    __tablename__ = "recommendation"

    recommendation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    session_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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


class RecommendationVersionModel(Base):
    """Immutable deterministic recommendation output with full trace."""

    __tablename__ = "recommendation_version"
    __table_args__ = (
        Index("ix_recommendation_version_rec_version", "recommendation_id", "version"),
        Index(
            "ix_recommendation_version_action_created_at",
            "action_type",
            "created_at",
        ),
    )

    recommendation_version_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    recommendation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recommendation.recommendation_id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    net_value_after_carry: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )
    partial_quantity_pct: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )
    recommendation_confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )
    net_hold_value_components: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rules_applied: Mapped[list] = mapped_column(JSONB, nullable=False)
    msp_proximity_triggered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    decision_trace: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    stability_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    supersedes_version_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey(
            "recommendation_version.recommendation_version_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_delivered: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="false",
    )


class OutcomeModel(Base):
    """Realized result for calibration — one row per session."""

    __tablename__ = "outcome"
    __table_args__ = (
        Index("ix_outcome_validation_status_recorded_at", "validation_status", "recorded_at"),
    )

    outcome_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    session_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, unique=True)
    session_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    realized_net_value: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4),
        nullable=True,
    )
    action_taken: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observation_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    observation_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    validation_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=OutcomeValidationStatus.PENDING.value,
    )
    validation_method: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ground_truth_refs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
