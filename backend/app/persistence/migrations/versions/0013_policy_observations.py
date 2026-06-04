"""Policy observations — structured government/policy events (PI10 Track B).

Revision ID: 0013_policy_observations
Revises: 0012_signal_pi9_contract
Create Date: 2026-06-04

E-01 append-only policy fact store; manual/seed ingest only (no NLP/LLM).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013_policy_observations"
down_revision: str | None = "0012_signal_pi9_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE policy_observation (
            observation_id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            commodity_id VARCHAR(64) NOT NULL,
            policy_type VARCHAR(64) NOT NULL,
            source VARCHAR(64) NOT NULL,
            published_date DATE NOT NULL,
            effective_date DATE NOT NULL,
            impact_direction VARCHAR(16) NOT NULL,
            confidence NUMERIC(5, 4) NOT NULL,
            summary VARCHAR(512),
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            provenance JSONB NOT NULL DEFAULT '{}',
            supersedes_id UUID,
            validation_status observation_validation_status NOT NULL DEFAULT 'received',
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id) ON DELETE CASCADE,
            CONSTRAINT ck_policy_confidence_range
                CHECK (confidence >= 0 AND confidence <= 1),
            CONSTRAINT ck_policy_impact_direction
                CHECK (impact_direction IN ('bullish', 'bearish', 'neutral'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_policy_commodity_effective_date
            ON policy_observation (commodity_id, effective_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_policy_type_effective_date
            ON policy_observation (policy_type, effective_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_policy_source_published_date
            ON policy_observation (source, published_date DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS policy_observation CASCADE")
