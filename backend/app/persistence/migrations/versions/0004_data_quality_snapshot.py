"""Data quality snapshot — per-refresh source health (E-01-S08).

Revision ID: 0004_data_quality_snapshot
Revises: 0003_commodity_registry
Create Date: 2026-06-04

TDS-006 §3.17; retention 2 years (documented in repository module).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_data_quality_snapshot"
down_revision: str | None = "0003_commodity_registry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_quality_snapshot",
        sa.Column(
            "quality_snapshot_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("commodity_id", sa.String(length=64), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column(
            "registry_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "source_health",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("overall_quality_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("agmarknet_lag_hours", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("futures_feed_ok", sa.Boolean(), nullable=False),
        sa.Column(
            "signals_missing",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "confidence_penalty_factor",
            sa.Numeric(precision=5, scale=4),
            nullable=False,
            server_default=sa.text("0"),
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
        sa.ForeignKeyConstraint(
            ["registry_id"],
            ["commodity_registry.registry_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("quality_snapshot_id"),
        sa.UniqueConstraint(
            "commodity_id",
            "as_of_date",
            "registry_id",
            name="uq_quality_commodity_date_registry",
        ),
    )
    op.create_index(
        "ix_quality_commodity_as_of_date",
        "data_quality_snapshot",
        ["commodity_id", "as_of_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_quality_commodity_as_of_date", table_name="data_quality_snapshot")
    op.drop_table("data_quality_snapshot")
