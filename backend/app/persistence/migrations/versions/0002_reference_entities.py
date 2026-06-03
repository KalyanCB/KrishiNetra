"""Reference entities — commodity, profile, region, market (E-01-S03).

Revision ID: 0002_reference_entities
Revises: 0001_alembic_bootstrap
Create Date: 2026-06-03

TDS-006 §3.1–3.5; TDS-009 §12 profile JSON fields.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_reference_entities"
down_revision: str | None = "0001_alembic_bootstrap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commodity",
        sa.Column("commodity_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "reference_implementation_flag",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("commodity_id"),
    )
    op.create_index(
        "ix_commodity_status_active",
        "commodity",
        ["status"],
        unique=False,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "commodity_profile",
        sa.Column("commodity_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column(
            "quality_dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "storage_characteristics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "participant_roles_enabled",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "phase_1_active_roles",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
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
        sa.PrimaryKeyConstraint("commodity_id"),
    )

    op.create_table(
        "region",
        sa.Column("region_id", sa.String(length=64), nullable=False),
        sa.Column("commodity_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("parent_region_id", sa.String(length=64), nullable=True),
        sa.Column(
            "external_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["commodity_id"],
            ["commodity.commodity_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_region_id"],
            ["region.region_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("region_id"),
    )
    op.create_index(
        "ix_region_commodity_type",
        "region",
        ["commodity_id", "type"],
        unique=False,
    )

    op.create_table(
        "market",
        sa.Column("market_id", sa.String(length=64), nullable=False),
        sa.Column("region_id", sa.String(length=64), nullable=False),
        sa.Column("commodity_id", sa.String(length=64), nullable=False),
        sa.Column("market_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "source_identifiers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["commodity_id"],
            ["commodity.commodity_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["region_id"],
            ["region.region_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("market_id"),
    )
    op.create_index(
        "ix_market_commodity_region",
        "market",
        ["commodity_id", "region_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_market_commodity_region", table_name="market")
    op.drop_table("market")
    op.drop_index("ix_region_commodity_type", table_name="region")
    op.drop_table("region")
    op.drop_table("commodity_profile")
    op.drop_index("ix_commodity_status_active", table_name="commodity")
    op.drop_table("commodity")
