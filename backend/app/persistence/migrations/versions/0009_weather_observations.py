"""Partitioned weather observations — district/regional daily facts (PI6 Track C).

Revision ID: 0009_weather_observations
Revises: 0008_decision_stack
Create Date: 2026-06-04

E-01 weather observation store; TDS/E-01 append-only pattern (not price_observation).
Reuses observation_validation_status from 0005.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009_weather_observations"
down_revision: str | None = "0008_decision_stack"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARTITION_START = "2026-06-01"
_PARTITION_END = "2026-07-01"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE weather_observation (
            observation_id UUID NOT NULL DEFAULT gen_random_uuid(),
            region_id VARCHAR(64) NOT NULL,
            commodity_id VARCHAR(64) NOT NULL,
            as_of_date DATE NOT NULL,
            rainfall_mm NUMERIC(10, 4),
            temperature_min_c NUMERIC(6, 2),
            temperature_max_c NUMERIC(6, 2),
            temperature_mean_c NUMERIC(6, 2),
            relative_humidity_pct NUMERIC(6, 2),
            district_name VARCHAR(255),
            observed_at TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            source VARCHAR(64) NOT NULL,
            provenance JSONB NOT NULL DEFAULT '{}',
            supersedes_id UUID,
            validation_status observation_validation_status NOT NULL DEFAULT 'received',
            PRIMARY KEY (observation_id, as_of_date),
            FOREIGN KEY (region_id) REFERENCES region(region_id) ON DELETE RESTRICT,
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id) ON DELETE CASCADE
        ) PARTITION BY RANGE (as_of_date)
        """
    )
    op.execute(
        f"""
        CREATE TABLE weather_observation_2026_06 PARTITION OF weather_observation
            FOR VALUES FROM ('{_PARTITION_START}') TO ('{_PARTITION_END}')
        """
    )
    op.execute(
        "CREATE TABLE weather_observation_default PARTITION OF weather_observation DEFAULT"
    )
    op.execute(
        """
        CREATE INDEX ix_weather_region_as_of_date
            ON weather_observation (region_id, as_of_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_weather_commodity_as_of_date
            ON weather_observation (commodity_id, as_of_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_weather_source_as_of_date
            ON weather_observation (source, as_of_date)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS weather_observation CASCADE")
