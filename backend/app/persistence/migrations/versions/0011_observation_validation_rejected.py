"""Add rejected to observation_validation_status (PI8 Track A).

Revision ID: 0011_observation_rejected
Revises: 0010_partition_backfill
Create Date: 2026-06-04

Extends observation lifecycle with rejected for QA failures while
received remains the draft/pending ingest state.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011_observation_rejected"
down_revision: str | None = "0010_partition_backfill"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE observation_validation_status ADD VALUE IF NOT EXISTS 'rejected'"
    )


def downgrade() -> None:
    # PostgreSQL cannot drop enum values without recreating the type.
    pass
