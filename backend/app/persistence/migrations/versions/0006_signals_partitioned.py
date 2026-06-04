"""Partitioned structured signals and signal snapshots — E-01-S05.

Revision ID: 0006_signals_partitioned
Revises: 0005_observations_partitioned
Create Date: 2026-06-04

TDS-006 §3.8–3.9, §9; monthly RANGE on structured_signal.as_of_date only.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006_signals_partitioned"
down_revision: str | None = "0005_observations_partitioned"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARTITION_START = "2026-06-01"
_PARTITION_END = "2026-07-01"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE structured_signal (
            signal_id UUID NOT NULL DEFAULT gen_random_uuid(),
            agent_type VARCHAR(32) NOT NULL,
            commodity_id VARCHAR(64) NOT NULL,
            as_of_date DATE NOT NULL,
            as_of_timestamp TIMESTAMPTZ NOT NULL,
            value NUMERIC(18, 4) NOT NULL,
            direction VARCHAR(16) NOT NULL,
            magnitude NUMERIC(5, 4) NOT NULL,
            confidence NUMERIC(5, 4) NOT NULL,
            signal_components JSONB,
            source_observation_refs JSONB,
            registry_id UUID NOT NULL,
            agent_version VARCHAR(64),
            PRIMARY KEY (signal_id, as_of_date),
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id)
                ON DELETE CASCADE,
            FOREIGN KEY (registry_id) REFERENCES commodity_registry(registry_id)
                ON DELETE RESTRICT
        ) PARTITION BY RANGE (as_of_date)
        """
    )
    op.execute(
        f"""
        CREATE TABLE structured_signal_2026_06 PARTITION OF structured_signal
            FOR VALUES FROM ('{_PARTITION_START}') TO ('{_PARTITION_END}')
        """
    )
    op.execute(
        "CREATE TABLE structured_signal_default PARTITION OF structured_signal DEFAULT"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_signal_commodity_date_agent_registry
            ON structured_signal (commodity_id, as_of_date, agent_type, registry_id)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_signal_as_of_date
            ON structured_signal (as_of_date DESC)
        """
    )

    op.execute(
        """
        CREATE TABLE signal_snapshot (
            snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            commodity_id VARCHAR(64) NOT NULL,
            as_of_date DATE NOT NULL,
            registry_id UUID NOT NULL,
            signal_ids JSONB NOT NULL,
            snapshot_hash VARCHAR(64) NOT NULL,
            data_quality_snapshot_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id)
                ON DELETE CASCADE,
            FOREIGN KEY (registry_id) REFERENCES commodity_registry(registry_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (data_quality_snapshot_id)
                REFERENCES data_quality_snapshot(quality_snapshot_id)
                ON DELETE SET NULL,
            CONSTRAINT uq_snapshot_commodity_date_registry
                UNIQUE (commodity_id, as_of_date, registry_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_snapshot_commodity_as_of_date
            ON signal_snapshot (commodity_id, as_of_date)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS signal_snapshot CASCADE")
    op.execute("DROP TABLE IF EXISTS structured_signal CASCADE")
