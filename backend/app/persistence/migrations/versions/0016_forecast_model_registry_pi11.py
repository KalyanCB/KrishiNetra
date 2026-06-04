"""PI11 Track E: forecast_model_registry + forecast_version link.

Revision ID: 0016_forecast_model_registry
Revises: 0015_forecast_quality_metric
Create Date: 2026-06-04

Stores trained-model metadata (version, training window, MAE/RMSE/MAPE,
feature_set id/hash). Optional FK from forecast_version (0007).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0016_forecast_model_registry"
down_revision: str | None = "0015_forecast_quality_metric"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE forecast_model_registry (
            forecast_model_registry_id UUID PRIMARY KEY
                DEFAULT gen_random_uuid(),
            commodity_id VARCHAR(64) NOT NULL,
            registry_id UUID NOT NULL,
            model_version VARCHAR(64) NOT NULL,
            model_family VARCHAR(64),
            horizon_days INTEGER NOT NULL DEFAULT 30,
            training_window_start DATE NOT NULL,
            training_window_end DATE NOT NULL,
            metrics JSONB NOT NULL,
            feature_set_id UUID,
            feature_set_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id)
                ON DELETE CASCADE,
            FOREIGN KEY (registry_id) REFERENCES commodity_registry(registry_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (feature_set_id) REFERENCES feature_set(feature_set_id)
                ON DELETE SET NULL,
            CHECK (training_window_start <= training_window_end),
            CHECK (horizon_days IN (30, 60, 90))
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_forecast_model_registry_version_window_hash
            ON forecast_model_registry (
                commodity_id,
                registry_id,
                model_version,
                training_window_start,
                training_window_end,
                feature_set_hash
            )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_forecast_model_registry_commodity_model
            ON forecast_model_registry (commodity_id, model_version)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_forecast_model_registry_feature_set_id
            ON forecast_model_registry (feature_set_id)
            WHERE feature_set_id IS NOT NULL
        """
    )
    op.execute(
        """
        ALTER TABLE forecast_version
            ADD COLUMN IF NOT EXISTS forecast_model_registry_id UUID
        """
    )
    op.execute(
        """
        ALTER TABLE forecast_version
            ADD CONSTRAINT fk_forecast_version_model_registry
                FOREIGN KEY (forecast_model_registry_id)
                REFERENCES forecast_model_registry(forecast_model_registry_id)
                ON DELETE SET NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_forecast_version_model_registry_id
            ON forecast_version (forecast_model_registry_id)
            WHERE forecast_model_registry_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_forecast_version_model_registry_id")
    op.execute(
        """
        ALTER TABLE forecast_version
            DROP CONSTRAINT IF EXISTS fk_forecast_version_model_registry
        """
    )
    op.execute(
        """
        ALTER TABLE forecast_version
            DROP COLUMN IF EXISTS forecast_model_registry_id
        """
    )
    op.execute("DROP TABLE IF EXISTS forecast_model_registry CASCADE")
