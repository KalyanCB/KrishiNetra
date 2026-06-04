"""Forecast quality metric persistence — PI11 Track D.

Revision ID: 0015_forecast_quality_metric
Revises: 0014_pi10_head_merge
Create Date: 2026-06-04

TDS-000 forecast KPIs (MAE, RMSE, MAPE); TDS-011 interval coverage.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_forecast_quality_metric"
down_revision: str | None = "0014_pi10_head_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forecast_quality_metric",
        sa.Column(
            "forecast_quality_id",
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
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column(
            "forecast_version_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "assessment_source",
            sa.String(length=32),
            nullable=False,
            server_default="backtest",
        ),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("mae", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("rmse", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("mape", sa.Numeric(precision=14, scale=4), nullable=True),
        sa.Column("coverage", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column(
            "metrics_detail",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
        sa.PrimaryKeyConstraint("forecast_quality_id"),
    )
    op.create_index(
        "uq_forecast_quality_commodity_date_registry_horizon",
        "forecast_quality_metric",
        [
            "commodity_id",
            "as_of_date",
            "registry_id",
            "horizon_days",
            "model_version",
            "assessment_source",
        ],
        unique=True,
    )
    op.create_index(
        "ix_forecast_quality_commodity_as_of_date",
        "forecast_quality_metric",
        ["commodity_id", "as_of_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_forecast_quality_commodity_as_of_date",
        table_name="forecast_quality_metric",
    )
    op.drop_index(
        "uq_forecast_quality_commodity_date_registry_horizon",
        table_name="forecast_quality_metric",
    )
    op.drop_table("forecast_quality_metric")
