"""Partitioned observation time-series — price and arrival (E-01-S04).

Revision ID: 0005_observations_partitioned
Revises: 0004_data_quality_snapshot
Create Date: 2026-06-04

TDS-006 §3.6–3.7, §4, §9; monthly RANGE on as_of_date + DEFAULT child.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_observations_partitioned"
down_revision: str | None = "0004_data_quality_snapshot"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Initial partition window: June 2026 (ops adds future months via forward migration).
_PARTITION_START = "2026-06-01"
_PARTITION_END = "2026-07-01"


def upgrade() -> None:
    op.execute(
        """
        CREATE TYPE observation_validation_status AS ENUM (
            'received', 'validated', 'published', 'superseded'
        )
        """
    )

    op.execute(
        """
        CREATE TABLE price_observation (
            observation_id UUID NOT NULL DEFAULT gen_random_uuid(),
            market_id VARCHAR(64) NOT NULL,
            commodity_id VARCHAR(64) NOT NULL,
            price_type VARCHAR(64) NOT NULL,
            value NUMERIC(18, 4) NOT NULL,
            unit VARCHAR(32) NOT NULL,
            currency VARCHAR(8) NOT NULL,
            observed_at TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            as_of_date DATE NOT NULL,
            source VARCHAR(128) NOT NULL,
            quality_grade VARCHAR(64),
            supersedes_id UUID,
            validation_status observation_validation_status NOT NULL DEFAULT 'received',
            PRIMARY KEY (observation_id, as_of_date),
            FOREIGN KEY (market_id) REFERENCES market(market_id) ON DELETE RESTRICT,
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id) ON DELETE CASCADE
        ) PARTITION BY RANGE (as_of_date)
        """
    )
    op.execute(
        f"""
        CREATE TABLE price_observation_2026_06 PARTITION OF price_observation
            FOR VALUES FROM ('{_PARTITION_START}') TO ('{_PARTITION_END}')
        """
    )
    op.execute(
        "CREATE TABLE price_observation_default PARTITION OF price_observation DEFAULT"
    )
    op.execute(
        """
        CREATE INDEX ix_price_commodity_as_of_date
            ON price_observation (commodity_id, as_of_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_price_market_observed_at
            ON price_observation (market_id, observed_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_price_source_as_of_date
            ON price_observation (source, as_of_date)
        """
    )

    op.execute(
        """
        CREATE TABLE arrival_observation (
            observation_id UUID NOT NULL DEFAULT gen_random_uuid(),
            market_id VARCHAR(64) NOT NULL,
            commodity_id VARCHAR(64) NOT NULL,
            volume NUMERIC(18, 4) NOT NULL,
            unit VARCHAR(32) NOT NULL,
            observed_at TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            as_of_date DATE NOT NULL,
            source VARCHAR(128) NOT NULL,
            supersedes_id UUID,
            validation_status observation_validation_status NOT NULL DEFAULT 'received',
            PRIMARY KEY (observation_id, as_of_date),
            FOREIGN KEY (market_id) REFERENCES market(market_id) ON DELETE RESTRICT,
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id) ON DELETE CASCADE
        ) PARTITION BY RANGE (as_of_date)
        """
    )
    op.execute(
        f"""
        CREATE TABLE arrival_observation_2026_06 PARTITION OF arrival_observation
            FOR VALUES FROM ('{_PARTITION_START}') TO ('{_PARTITION_END}')
        """
    )
    op.execute(
        "CREATE TABLE arrival_observation_default PARTITION OF arrival_observation DEFAULT"
    )
    op.execute(
        """
        CREATE INDEX ix_arrival_commodity_as_of_date
            ON arrival_observation (commodity_id, as_of_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_arrival_market_observed_at
            ON arrival_observation (market_id, observed_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS arrival_observation CASCADE")
    op.execute("DROP TABLE IF EXISTS price_observation CASCADE")
    op.execute("DROP TYPE IF EXISTS observation_validation_status")
