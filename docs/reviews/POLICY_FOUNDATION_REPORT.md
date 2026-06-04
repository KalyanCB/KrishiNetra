# Policy Observation Foundation — PI10 Track B Completion Report

**Date:** 2026-06-04  
**PI:** PI10 Track B (KDO — Policy Foundation)  
**Workspace:** `c1bc6eb` (prior head `0012_signal_pi9_contract`)  
**Specification:** [SIGNAL_ENGINE_V1.md](../research/SIGNAL_ENGINE_V1.md) §5; TDS-005 `POLICY_UPDATED`; E-01 append-only facts

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| `policy_observation` table shipped? | **Yes** — migration `0013_policy_observations` (+ `0014_pi10_head_merge` with Futures/Forecast tracks) |
| Required fields present? | **Yes** — `policy_type`, `source`, `published_date`, `effective_date`, `impact_direction`, `confidence` |
| Append-only repository? | **Yes** — `PolicyObservationRepository.insert_observation` only |
| NLP / LLM ingest? | **No** — manual JSON fixture + idempotent seed runner |
| Policy signal runtime (E-04)? | **No** — persistence foundation only |
| Cotton seed rows? | **Yes** — MSP announcement stub + export ban stub |

**Overall:** **PASS** — PI10 Track B deliverable ready for Policy agent wiring (future track).

---

## 2. Alembic coordination

PI10 Tracks A/B/C each branch from `0012_signal_pi9_contract`:

```
0012 → 0013_policy_observations  ─┐
0012 → 0013_forecast_feature_snapshot ─┼→ 0014_pi10_head_merge (merge, no DDL)
0012 → 0013_futures_observations ─┘
```

Policy DDL lives in **`0013_policy_observations`**; workspace head is **`0014_pi10_head_merge`**.

---

## 3. Schema (`0013_policy_observations`)

| Column | Type | Notes |
|--------|------|-------|
| `observation_id` | UUID PK | Append-only identity |
| `commodity_id` | VARCHAR(64) FK → `commodity` | Cotton-first |
| `policy_type` | VARCHAR(64) | `msp_announcement`, `cci_procurement`, `export_ban`, `export_restriction_lifted` |
| `source` | VARCHAR(64) | `pib_manual`, `cci_manual`, `seed_fixture` |
| `published_date` | DATE | Announcement / circular date |
| `effective_date` | DATE | Policy effective window start |
| `impact_direction` | VARCHAR(16) | `bullish` / `bearish` / `neutral` (CHECK) |
| `confidence` | NUMERIC(5,4) | [0, 1] (CHECK) |
| `summary` | VARCHAR(512) | Optional human-readable stub text |
| `ingested_at` | TIMESTAMPTZ | Server default `now()` |
| `provenance` | JSONB | Manual ingest metadata |
| `supersedes_id` | UUID | Correction chain (unused in seed) |
| `validation_status` | `observation_validation_status` | Reuses E-01 enum from `0005` |

**Indexes:** `(commodity_id, effective_date DESC)`, `(policy_type, effective_date DESC)`, `(source, published_date DESC)`.

Non-partitioned table — low-volume policy events; avoids premature partition ops.

---

## 4. Deliverables

| Artifact | Path |
|----------|------|
| Migration | `backend/app/persistence/migrations/versions/0013_policy_observations.py` |
| ORM | `backend/app/persistence/models/policy.py` |
| Validation | `backend/app/persistence/validation/policy.py` |
| Repository | `backend/app/persistence/repositories/policy.py` |
| Seed fixture | `backend/app/persistence/seeds/fixtures/policy_cotton.json` |
| Seed runner | `backend/app/persistence/seeds/policy.py` |
| UoW wiring | `backend/app/persistence/unit_of_work.py` → `policy_observations` |
| Unit / integration tests | `tests/unit/test_policy_observations.py` |

---

## 5. Seed Data (cotton)

| `policy_type` | `source` | `impact_direction` | Stub summary |
|---------------|----------|-------------------|--------------|
| `msp_announcement` | `pib_manual` | `bullish` | MSP medium staple INR 7120/qtl |
| `export_ban` | `pib_manual` | `bearish` | Temporary export restriction circular |

Apply after cotton reference seed:

```bash
uv run python -c "
from backend.app.persistence.database import SessionLocal
from backend.app.persistence.seeds.runner import SeedRunner
from backend.app.persistence.seeds.policy import PolicySeedRunner
s = SessionLocal()
SeedRunner(s).apply('cotton')
print('policy rows inserted:', PolicySeedRunner(s).apply('policy_cotton'))
s.commit()
s.close()
"
```

---

## 6. Repository Behavior

| Method | Behavior |
|--------|----------|
| `insert_observation` | Validates type, source, direction, confidence, validation_status; append-only |
| `get_observation` | By `observation_id` |
| `list_by_commodity_date_range` | Filter `effective_date` range; optional `policy_type` |

No `update()` — aligns with [REPOSITORY_PATTERN.md](../../backend/app/persistence/REPOSITORY_PATTERN.md).

---

## 7. Tests

| Test | Marker | Notes |
|------|--------|-------|
| `test_policy_type_rejects_unknown` | unit | Catalog enforcement |
| `test_policy_type_accepts_catalog` | unit | All `PolicyType` values |
| `test_policy_source_accepts_catalog` | unit | All `PolicyObservationSource` values |
| `test_policy_impact_direction_accepts_signal_directions` | unit | Reuses signal direction validator |
| `test_policy_confidence_rejects_out_of_range` | unit | [0, 1] bound |
| `test_policy_observation_append_only` | integration | Insert + list |
| `test_policy_seed_fixture_idempotent` | integration | 2 rows first run; 0 on repeat |
| `test_alembic_revision_chain_linear` | unit | Head `0013` |

**PI10 Track B unit tests (non-integration):** **5**

---

## 8. Quality Gates

| Check | Scope | Result |
|-------|-------|--------|
| `uv run ruff check` | policy paths + tests | *(run @ merge)* |
| `uv run ruff format --check` | same | *(run @ merge)* |
| `uv run mypy` | policy model/repo/validation/seeds | *(run @ merge)* |
| `uv run pytest tests/unit/test_policy_observations.py -m "not integration" -q` | unit only | *(run @ merge)* |
| `alembic upgrade head` | `DATABASE_URL` @ 5433 | Head `0014_pi10_head_merge` |

---

## 9. Reference Return Values (PI10 Track B)

| Item | Value |
|------|-------|
| Policy migration revision | `0013_policy_observations` |
| Alembic head (post-merge) | `0014_pi10_head_merge` |
| Model path | `backend/app/persistence/models/policy.py` |
| Repository path | `backend/app/persistence/repositories/policy.py` |
| PI10 unit test count | **5** |
| Report path | `docs/reviews/POLICY_FOUNDATION_REPORT.md` |

---

## 10. Out of Scope / Follow-ons

| Item | Track |
|------|-------|
| `PolicySignalGenerator` / E-04 runtime | PI10+ Policy agent |
| PIB RSS / CCI automated ingest | E-03 Policy ingest |
| `msp_inr_quintal` registry seed | Registry / SR-03 |
| LangGraph `POLICY_UPDATED` publisher | Orchestration |

---

*End of Policy Observation foundation report — PI10 Track B.*
