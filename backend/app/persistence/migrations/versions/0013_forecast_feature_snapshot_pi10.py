"""PI10 Track C: ForecastFeatureSnapshot contract on feature_set.

Revision ID: 0013_forecast_feature_snapshot
Revises: 0012_signal_pi9_contract
Create Date: 2026-06-04

Extends feature_set (0007) with trace_id, feature_values JSONB map, and
feature_lineage JSONB — no duplicate feature store tables.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0013_forecast_feature_snapshot"
down_revision: str | None = "0012_signal_pi9_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE feature_set
            ADD COLUMN IF NOT EXISTS trace_id UUID
        """
    )
    op.execute(
        """
        ALTER TABLE feature_set
            ADD COLUMN IF NOT EXISTS feature_values JSONB NOT NULL DEFAULT '{}'::jsonb
        """
    )
    op.execute(
        """
        ALTER TABLE feature_set
            ADD COLUMN IF NOT EXISTS feature_lineage JSONB NOT NULL DEFAULT '{}'::jsonb
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_feature_set_trace_id
            ON feature_set (trace_id)
            WHERE trace_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_feature_set_commodity_date_registry
            ON feature_set (commodity_id, as_of_date, registry_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_feature_set_commodity_date_registry")
    op.execute("DROP INDEX IF EXISTS ix_feature_set_trace_id")
    op.execute(
        """
        ALTER TABLE feature_set
            DROP COLUMN IF EXISTS feature_lineage
        """
    )
    op.execute(
        """
        ALTER TABLE feature_set
            DROP COLUMN IF EXISTS feature_values
        """
    )
    op.execute(
        """
        ALTER TABLE feature_set
            DROP COLUMN IF EXISTS trace_id
        """
    )
