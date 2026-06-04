"""Commodity registry — versioned operational config (E-01-S10).

Revision ID: 0003_commodity_registry
Revises: 0002_reference_entities
Create Date: 2026-06-04

TDS-006 §3.3 + ADR-003 required/optional agents, signal_weights, regime_priority.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_commodity_registry"
down_revision: str | None = "0002_reference_entities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commodity_registry",
        sa.Column(
            "registry_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("commodity_id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "price_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "arrival_sources",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "demand_drivers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "policy_drivers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "weather_variables",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "forecast_horizons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[30, 60, 90]'::jsonb"),
        ),
        sa.Column(
            "required_agents",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "optional_agents",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "signal_weights",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "regime_priority",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "decision_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["commodity_id"],
            ["commodity.commodity_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("registry_id"),
        sa.UniqueConstraint("commodity_id", "version", name="uq_registry_commodity_version"),
    )
    op.create_index(
        "ix_registry_commodity_active",
        "commodity_registry",
        ["commodity_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("ix_registry_commodity_active", table_name="commodity_registry")
    op.drop_table("commodity_registry")
