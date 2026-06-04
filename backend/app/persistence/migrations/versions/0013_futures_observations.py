"""Partitioned futures observations — NCDEX KAPAS EOD (PI10 Track A).

Revision ID: 0013_futures_observations
Revises: 0012_signal_pi9_contract
Create Date: 2026-06-04

E-04 FuturesObservation store; append-only pattern aligned to weather_observation.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013_futures_observations"
down_revision: str | None = "0012_signal_pi9_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARTITION_START = "2026-06-01"
_PARTITION_END = "2026-07-01"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE futures_observation (
            observation_id UUID NOT NULL DEFAULT gen_random_uuid(),
            as_of_date DATE NOT NULL,
            commodity_id VARCHAR(64) NOT NULL,
            contract_symbol VARCHAR(32) NOT NULL,
            expiry_date DATE NOT NULL,
            settle_price NUMERIC(18, 4) NOT NULL,
            quote_unit VARCHAR(32) NOT NULL,
            settle_price_quintal NUMERIC(18, 4) NOT NULL,
            open_interest INTEGER,
            volume NUMERIC(18, 4),
            observed_at TIMESTAMPTZ NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            source VARCHAR(128) NOT NULL,
            environment VARCHAR(32) NOT NULL,
            provenance JSONB NOT NULL DEFAULT '{}',
            supersedes_id UUID,
            validation_status observation_validation_status NOT NULL DEFAULT 'received',
            PRIMARY KEY (observation_id, as_of_date),
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id) ON DELETE CASCADE
        ) PARTITION BY RANGE (as_of_date)
        """
    )
    op.execute(
        f"""
        CREATE TABLE futures_observation_2026_06 PARTITION OF futures_observation
            FOR VALUES FROM ('{_PARTITION_START}') TO ('{_PARTITION_END}')
        """
    )
    op.execute(
        "CREATE TABLE futures_observation_default PARTITION OF futures_observation DEFAULT"
    )
    op.execute(
        """
        CREATE INDEX ix_futures_commodity_as_of_date
            ON futures_observation (commodity_id, as_of_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_futures_contract_as_of_date
            ON futures_observation (contract_symbol, as_of_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_futures_source_as_of_date
            ON futures_observation (source, as_of_date)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_futures_expiry_as_of_date
            ON futures_observation (expiry_date, as_of_date)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS futures_observation CASCADE")
