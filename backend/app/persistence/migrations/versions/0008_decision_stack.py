"""Decision session stack — user context through outcome (E-01-S07).

Revision ID: 0008_decision_stack
Revises: 0007_forecast_and_features
Create Date: 2026-06-04

TDS-006 §3.12–3.16, §9; quarterly RANGE on decision_session.created_at only.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008_decision_stack"
down_revision: str | None = "0007_forecast_and_features"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Q2 2026 partition window (ops adds future quarters via forward migration).
_PARTITION_START = "2026-04-01"
_PARTITION_END = "2026-07-01"


def _create_enum_if_not_exists(name: str, values_sql: str) -> None:
    """Idempotent enum creation for downgrade/re-upgrade test cycles."""
    op.execute(
        f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({values_sql});
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )


def upgrade() -> None:
    _create_enum_if_not_exists("persona_type", "'farmer', 'trader'")
    _create_enum_if_not_exists("liquidity_need", "'low', 'medium', 'high'")
    _create_enum_if_not_exists(
        "action_type",
        "'SELL', 'HOLD', 'PARTIAL_SELL', 'PARTIAL_HOLD'",
    )
    _create_enum_if_not_exists(
        "outcome_validation_status",
        "'pending', 'validated', 'rejected'",
    )

    op.execute(
        """
        CREATE TABLE user_context (
            context_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            commodity_id VARCHAR(64) NOT NULL,
            quantity NUMERIC(18, 4) NOT NULL,
            storage_access BOOLEAN NOT NULL DEFAULT true,
            liquidity_need liquidity_need NOT NULL,
            financing_profile JSONB NOT NULL,
            risk_profile JSONB NOT NULL,
            persona_type persona_type NOT NULL,
            region_preference VARCHAR(128),
            position_label VARCHAR(128),
            captured_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            context_hash VARCHAR(64) NOT NULL,
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id)
                ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_user_context_persona_captured_at
            ON user_context (persona_type, captured_at DESC)
        """
    )

    op.execute(
        """
        CREATE TABLE decision_session (
            session_id UUID NOT NULL DEFAULT gen_random_uuid(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            context_id UUID NOT NULL,
            commodity_id VARCHAR(64) NOT NULL,
            as_of_date DATE NOT NULL,
            registry_id UUID NOT NULL,
            forecast_version_id UUID NOT NULL,
            snapshot_id UUID NOT NULL,
            mi_snapshot_ref VARCHAR(256),
            recommendation_id UUID,
            explanation_id UUID,
            persona_type persona_type NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'pending',
            delivered_at TIMESTAMPTZ,
            PRIMARY KEY (session_id, created_at),
            FOREIGN KEY (context_id) REFERENCES user_context(context_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id)
                ON DELETE CASCADE,
            FOREIGN KEY (registry_id) REFERENCES commodity_registry(registry_id)
                ON DELETE RESTRICT,
            FOREIGN KEY (forecast_version_id, as_of_date)
                REFERENCES forecast_version(forecast_version_id, as_of_date)
                ON DELETE RESTRICT,
            FOREIGN KEY (snapshot_id) REFERENCES signal_snapshot(snapshot_id)
                ON DELETE RESTRICT
        ) PARTITION BY RANGE (created_at)
        """
    )
    op.execute(
        f"""
        CREATE TABLE decision_session_2026_q2 PARTITION OF decision_session
            FOR VALUES FROM ('{_PARTITION_START}') TO ('{_PARTITION_END}')
        """
    )
    op.execute(
        "CREATE TABLE decision_session_default PARTITION OF decision_session DEFAULT"
    )
    op.execute(
        """
        CREATE INDEX ix_decision_session_commodity_as_of_date
            ON decision_session (commodity_id, as_of_date DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_decision_session_context_id
            ON decision_session (context_id)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_decision_session_status_created_at
            ON decision_session (status, created_at)
        """
    )

    op.execute(
        """
        CREATE TABLE recommendation (
            recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL,
            session_created_at TIMESTAMPTZ NOT NULL,
            commodity_id VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            FOREIGN KEY (session_id, session_created_at)
                REFERENCES decision_session(session_id, created_at)
                ON DELETE CASCADE,
            FOREIGN KEY (commodity_id) REFERENCES commodity(commodity_id)
                ON DELETE CASCADE,
            UNIQUE (session_id)
        )
        """
    )

    op.execute(
        """
        ALTER TABLE decision_session
            ADD CONSTRAINT fk_decision_session_recommendation
            FOREIGN KEY (recommendation_id)
                REFERENCES recommendation(recommendation_id)
                ON DELETE SET NULL
        """
    )

    op.execute(
        """
        CREATE TABLE recommendation_version (
            recommendation_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            recommendation_id UUID NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            action_type action_type NOT NULL,
            net_value_after_carry NUMERIC(18, 4) NOT NULL,
            partial_quantity_pct NUMERIC(5, 4),
            recommendation_confidence NUMERIC(5, 4) NOT NULL,
            net_hold_value_components JSONB,
            rules_applied JSONB NOT NULL DEFAULT '[]',
            msp_proximity_triggered BOOLEAN NOT NULL DEFAULT false,
            formula_version VARCHAR(64) NOT NULL,
            decision_trace JSONB,
            stability_token VARCHAR(128),
            supersedes_version_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            is_delivered BOOLEAN NOT NULL DEFAULT false,
            FOREIGN KEY (recommendation_id)
                REFERENCES recommendation(recommendation_id)
                ON DELETE CASCADE,
            FOREIGN KEY (supersedes_version_id)
                REFERENCES recommendation_version(recommendation_version_id)
                ON DELETE SET NULL
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_recommendation_version_rec_version
            ON recommendation_version (recommendation_id, version)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_recommendation_version_action_created_at
            ON recommendation_version (action_type, created_at)
        """
    )

    op.execute(
        """
        CREATE TABLE outcome (
            outcome_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL,
            session_created_at TIMESTAMPTZ NOT NULL,
            realized_net_value NUMERIC(18, 4),
            action_taken VARCHAR(64),
            observation_period_start DATE,
            observation_period_end DATE,
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            validation_status outcome_validation_status NOT NULL DEFAULT 'pending',
            validation_method VARCHAR(128),
            ground_truth_refs JSONB,
            FOREIGN KEY (session_id, session_created_at)
                REFERENCES decision_session(session_id, created_at)
                ON DELETE CASCADE,
            UNIQUE (session_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_outcome_validation_status_recorded_at
            ON outcome (validation_status, recorded_at)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS outcome CASCADE")
    op.execute("DROP TABLE IF EXISTS recommendation_version CASCADE")
    op.execute(
        """
        ALTER TABLE decision_session
            DROP CONSTRAINT IF EXISTS fk_decision_session_recommendation
        """
    )
    op.execute("DROP TABLE IF EXISTS recommendation CASCADE")
    op.execute("DROP TABLE IF EXISTS decision_session CASCADE")
    op.execute("DROP TABLE IF EXISTS user_context CASCADE")
    op.execute("DROP TYPE IF EXISTS outcome_validation_status")
    op.execute("DROP TYPE IF EXISTS action_type")
    op.execute("DROP TYPE IF EXISTS liquidity_need")
    op.execute("DROP TYPE IF EXISTS persona_type")
