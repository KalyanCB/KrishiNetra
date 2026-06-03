"""Alembic bootstrap — no business tables (E-01-S01).

Revision ID: 0001_alembic_bootstrap
Revises:
Create Date: 2026-06-03

Per E01_EXECUTION_PLAN §4 rev 0: schema versioning only; reference DDL in 0002.
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "0001_alembic_bootstrap"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op bootstrap; establishes migration chain before reference entities."""
    pass


def downgrade() -> None:
    pass
