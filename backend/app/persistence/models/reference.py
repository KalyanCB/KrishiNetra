"""Reference entity ORM models — TDS-006 §3.1–3.5 (E-01-S03)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.persistence.database import Base


class CommodityStatus(StrEnum):
    """Commodity lifecycle status (TDS-006 §3.1)."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class RegionType(StrEnum):
    """Region segmentation type (TDS-006 §3.4)."""

    STATE = "state"
    MANDI = "mandi"
    ZONE = "zone"


class CommodityModel(Base):
    """Root commodity identity (TDS-006 §3.1)."""

    __tablename__ = "commodity"

    commodity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=CommodityStatus.DRAFT.value,
    )
    reference_implementation_flag: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    profile: Mapped[CommodityProfileModel | None] = relationship(
        back_populates="commodity",
        uselist=False,
    )


class CommodityProfileModel(Base):
    """Static commodity metadata (TDS-006 §3.2, TDS-009 §12)."""

    __tablename__ = "commodity_profile"

    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="quintal")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="INR")
    quality_dimensions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    storage_characteristics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    participant_roles_enabled: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    phase_1_active_roles: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    commodity: Mapped[CommodityModel] = relationship(back_populates="profile")


class RegionModel(Base):
    """Geographic segmentation (TDS-006 §3.4)."""

    __tablename__ = "region"
    __table_args__ = (Index("ix_region_commodity_type", "commodity_id", "type"),)

    region_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_region_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("region.region_id", ondelete="SET NULL"),
        nullable=True,
    )
    external_refs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    commodity: Mapped[CommodityModel] = relationship()
    markets: Mapped[list[MarketModel]] = relationship(back_populates="region")


class MarketModel(Base):
    """Price discovery venue (TDS-006 §3.5)."""

    __tablename__ = "market"
    __table_args__ = (Index("ix_market_commodity_region", "commodity_id", "region_id"),)

    market_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    region_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("region.region_id", ondelete="CASCADE"),
        nullable=False,
    )
    commodity_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("commodity.commodity_id", ondelete="CASCADE"),
        nullable=False,
    )
    market_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_identifiers: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    region: Mapped[RegionModel] = relationship(back_populates="markets")
    commodity: Mapped[CommodityModel] = relationship()
