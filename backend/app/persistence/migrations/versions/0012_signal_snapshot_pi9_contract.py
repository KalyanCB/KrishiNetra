"""PI9 Track C: trace_id and PI9 signal bundle on signal_snapshot.

Revision ID: 0012_signal_pi9_contract
Revises: 0011_observation_rejected
Create Date: 2026-06-04

Adds orchestration trace_id to structured_signal and signal_snapshot, and
signals JSONB on signal_snapshot for PI9 contract rows (signal_type, direction,
magnitude, confidence, signal_inputs, as_of_date).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012_signal_pi9_contract"
down_revision: str | None = "0011_observation_rejected"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE structured_signal
            ADD COLUMN IF NOT EXISTS trace_id UUID
        """
    )
    op.execute(
        """
        ALTER TABLE signal_snapshot
            ADD COLUMN IF NOT EXISTS trace_id UUID
        """
    )
    op.execute(
        """
        ALTER TABLE signal_snapshot
            ADD COLUMN IF NOT EXISTS signals JSONB NOT NULL DEFAULT '[]'::jsonb
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_snapshot_trace_id
            ON signal_snapshot (trace_id)
            WHERE trace_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_snapshot_trace_id")
    op.execute(
        """
        ALTER TABLE signal_snapshot
            DROP COLUMN IF EXISTS signals
        """
    )
    op.execute(
        """
        ALTER TABLE signal_snapshot
            DROP COLUMN IF EXISTS trace_id
        """
    )
    op.execute(
        """
        ALTER TABLE structured_signal
            DROP COLUMN IF EXISTS trace_id
        """
    )
