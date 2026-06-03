# E-01-S03 Report — Reference Entity Tables

**Story:** E-01-S03 | **Status:** Done | **Date:** 2026-06-03

## Acceptance criteria evidence

| AC | Evidence |
|----|----------|
| AC-1 | Tables `commodity`, `commodity_profile`, `region`, `market` in `0002_reference_entities` |
| AC-2 | Partial index `ix_commodity_status_active`; `ix_market_commodity_region`; `ix_region_commodity_type` |
| AC-3 | JSONB: `quality_dimensions`, `storage_characteristics`, `participant_roles_enabled`, `phase_1_active_roles` |
| AC-4 | FKs: profile→commodity, region→commodity, market→region (+ commodity) |
| AC-5 | Reversible migration; `test_alembic_downgrade_one_revision` |

## Implementation

| Artifact | Purpose |
|----------|---------|
| `models/reference.py` | SQLAlchemy 2.x mapped models |
| `migrations/versions/0002_reference_entities.py` | DDL |
| `seeds/` | Framework stub; E-02 adds cotton fixture |

## Test results

```
uv run pytest tests/integration/test_reference_entities.py -v  → 3 passed (with DATABASE_URL)
uv run pytest tests/unit/test_seed_framework.py -v  → 2 passed
```

## ADR / TDS compliance

- TDS-006 §3.1–3.5 entity shapes
- TDS-009 §12 participant role JSON fields on profile
- No cotton seed (E-02)

## Risks

- `region_id` / `market_id` use string PKs (stable codes); UUID migration would be breaking
- Seed runner `NotImplementedError` until E-02
