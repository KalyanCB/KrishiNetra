"""Forecast, ForecastVersion, feature store — E-01-S06.

Revision ID: 0007_forecast_and_features
Revises: 0006_signals_partitioned
Create Date: 2026-06-04

TDS-006 §3.10–3.11, §10, §9; monthly RANGE on forecast_version.as_of_date only.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_forecast_and_features"
down_revision: str | None = "0006_signals_partitioned"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARTITION_START = "2026-06-01"
_PARTITION_END = "2026-07-01"


def upgrade() -> None:
    op.execute(
        """
        CREATE TYPE forecast_status AS ENUM ('complete', 'failed', 'partial')
        """
    )

    op.execute(
        """
        CREATE TABLE forecast (
            forecast_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            commodity_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id)
                ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_forecast_commodity_id
            ON forecast (commodity_id)
        """
    )

    op.execute(
        """
        CREATE TABLE feature_set (
            feature_set_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            commodity_id VARCHAR(64) NOT NULL,
            as_of_date DATE NOT NULL,
            registry_id UUID NOT NULL,
            feature_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id)
                ON DELETE CASCADE,
            FOREIGN KEY (registry_id) REFERENCES commodity_registry(registry_id)
                ON DELETE RESTRICT
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_feature_set_commodity_as_of_date
            ON feature_set (commodity_id, as_of_date)
        """
    )

    op.execute(
        """
        CREATE TABLE feature_vector (
            feature_set_id UUID NOT NULL,
            feature_name VARCHAR(128) NOT NULL,
            feature_value JSONB NOT NULL,
            PRIMARY KEY (feature_set_id, feature_name),
            FOREIGN KEY (feature_set_id) REFERENCES feature_set(feature_set_id)
                ON DELETE CASCADE
        )
        """
    )

    op.execute(
        """
        CREATE TABLE forecast_version (
            forecast_version_id UUID NOT NULL DEFAULT gen_random_uuid(),
            forecast_id UUID NOT NULL,
            commodity_id VARCHAR(64) NOT NULL,
            as_of_date DATE NOT NULL,
            registry_id UUID NOT NULL,
            snapshot_id UUID NOT NULL,
            model_family VARCHAR(64),
            model_version VARCHAR(64) NOT NULL,
            horizon_30 JSONB,
            horizon_60 JSONB,
            horizon_90 JSONB,
            feature_set_ref UUID,
            composed_signal_refs JSONB,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            status forecast_status NOT NULL DEFAULT 'complete',
            is_published BOOLEAN NOT NULL DEFAULT false,
            PRIMARY KEY (forecast_version_id, as_of_date),
            FOREIGN KEY (forecast_id) REFERENCES forecast(forecast_id)
                ON DELETE CASCADE,
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id)
                ON DELETE CASCADE,
            FOREIGN KEY (registry_id) REFERENCES commodity_registry(registry_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (snapshot_id) REFERENCES signal_snapshot(snapshot_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (feature_set_ref) REFERENCES feature_set(feature_set_id)
                ON DELETE SET NULL
        ) PARTITION BY RANGE (as_of_date)
        """
    )
    op.execute(
        f"""
        CREATE TABLE forecast_version_2026_06 PARTITION OF forecast_version
            FOR VALUES FROM ('{_PARTITION_START}') TO ('{_PARTITION_END}')
        """
    )
    op.execute(
        "CREATE TABLE forecast_version_default PARTITION OF forecast_version DEFAULT"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_forecast_version_commodity_date_model_registry
            ON forecast_version (commodity_id, as_of_date, model_version, registry_id)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_forecast_version_as_of_date_published
            ON forecast_version (as_of_date DESC, is_published)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_forecast_version_snapshot_id
            ON forecast_version (snapshot_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS forecast_version CASCADE")
    op.execute("DROP TABLE IF EXISTS feature_vector CASCADE")
    op.execute("DROP TABLE IF EXISTS feature_set CASCADE")
    op.execute("DROP TABLE IF EXISTS forecast CASCADE")
    op.execute("DROP TYPE IF EXISTS forecast_status")
