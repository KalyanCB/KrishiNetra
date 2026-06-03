# E-01 — Data Foundation

| Field | Value |
|-------|-------|
| **Epic ID** | E-01 |
| **Goal** | PostgreSQL canonical model per TDS-006; migrations; Redis MI key contract; retention hooks |
| **TDS** | TDS-006, TDS-005 |
| **REQ** | REQ-090, REQ-070 |
| **FD** | FD-023 |
| **Milestone** | M1 |
| **Sprint** | Sprint 1 (starts in Sprint 0 per TDS-014) |

## Feature Map

| Feature ID | Stories |
|------------|---------|
| F-01-01 Core entities | E-01-S01, E-01-S02, E-01-S03 |
| F-01-02 Observation TS | E-01-S04 |
| F-01-03 SignalSnapshot | E-01-S05 |
| F-01-04 ForecastVersion | E-01-S06 |
| F-01-05 DecisionSession stack | E-01-S07 |
| F-01-06 DataQualitySnapshot | E-01-S08 |
| F-01-07 Redis MI projection | E-01-S09 |
| (Feature store tables) | E-01-S10 |
| Integration | E-01-S11 |

**Explicitly out of scope:** `InventoryPosition` (Phase 2, E-12, TDS-009 §13)

---

## E-01-S01 — Database Migration Framework

### Summary

Alembic + SQLAlchemy async/sync session setup connected to PostgreSQL per ADR-002.

### Dependencies

| Dependency | Type |
|------------|------|
| E-00-S06 | Blocks (local PostgreSQL) |
| E-00-S02 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Alembic initialized under `backend/app/persistence/migrations/` |
| AC-2 | `alembic upgrade head` runs against empty local DB |
| AC-3 | SQLAlchemy models base + session factory in `backend/app/persistence/` |
| AC-4 | Migration naming convention documented |
| AC-5 | CI job runs migrations on ephemeral Postgres service container |

### Definition of Done

- [ ] ADR-002 accepted
- [ ] README documents upgrade/downgrade commands
- [ ] No business tables until E-01-S03+ migrations

### Technical Notes

- Use `UUID` PKs where TDS-006 specifies UUID
- `as_of_date` as `DATE` column type (TDS-013 §5.2)
- Money fields: `Numeric` not float for observation prices (prep for recommendations)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md), [ADR-002](../adrs/ADR-002-schema-migrations-alembic.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_alembic_upgrade_head` | Integration test on Testcontainers or compose Postgres |
| CI | Migration apply on PR |

### Traceability

REQ-090 | TDS-006 | ADR-002

---

## E-01-S02 — Persistence Repositories Base Pattern

### Summary

Repository interfaces and base CRUD patterns for append-only vs immutable-versioned entities.

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S01 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Repository pattern documented: append-only (observations), immutable insert-only (ForecastVersion, RecommendationVersion), versioned config (CommodityRegistry) |
| AC-2 | Base repository provides `get_by_id`, `insert`; no in-place UPDATE on immutable version tables |
| AC-3 | Transaction boundary helper for unit of work |
| AC-4 | Repositories live under `backend/app/persistence/repositories/` |

### Definition of Done

- [ ] Pattern used by at least one stub repository in E-01-S03
- [ ] Code review confirms immutability rules match TDS-006 §6–§7

### Technical Notes

- Enforce "never UPDATE published numeric fields" on ForecastVersion at repository layer (TDS-006 §6)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §6–§8

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_repository_insert_only_forecast_version` | Attempt update raises or is blocked |

### Traceability

FD-014, NFR-REP-001 | TDS-006 §6

---

## E-01-S03 — Commodity, CommodityProfile, Region, Market Tables

### Summary

DDL and SQLAlchemy models for reference entities. **No cotton seed data** (E-02).

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S01 | Blocks |
| E-01-S02 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Tables: `commodity`, `commodity_profile`, `region`, `market` per TDS-006 §3.1–3.5 |
| AC-2 | Indexes: PKs; `commodity.status` partial index; `(commodity_id, region_id)` on market |
| AC-3 | `commodity_profile` includes JSON columns for `quality_dimensions`, `storage_characteristics`, `participant_roles_enabled`, `phase_1_active_roles` (TDS-009 §12) |
| AC-4 | FK: profile→commodity, region→commodity, market→region |
| AC-5 | Migrations reversible |

### Definition of Done

- [ ] Migration applied locally
- [ ] Empty tables queryable
- [ ] E-02 can insert cotton seed without schema change

### Technical Notes

- `participant_roles_enabled`: array/JSON of six roles (Farmer, Trader, Ginner, Miller, Exporter, Aggregator)
- `reference_implementation_flag` on commodity for cotton (E-02 sets true)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §3.1–3.5, [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) §12

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_commodity_profile_fk` | Insert commodity + profile succeeds |
| `test_region_market_hierarchy` | Region→Market FK enforced |

### Traceability

REQ-090, REQ-073 | TDS-006 | FD-022

---

## E-01-S04 — PriceObservation and ArrivalObservation (Time-Series)

### Summary

Append-only observation tables with indexes and monthly range partitioning per TDS-006 §4, §9.

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S03 | Blocks (market FK) |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Tables `price_observation`, `arrival_observation` with all TDS-006 §3.6–3.7 attributes |
| AC-2 | Indexes: `(commodity_id, as_of_date DESC)`, `(market_id, observed_at DESC)` |
| AC-3 | Monthly RANGE partition on `as_of_date` (initial partition + default) |
| AC-4 | `supersedes_id` nullable self-FK supported |
| AC-5 | `validation_status` enum: received, validated, published, superseded |

### Definition of Done

- [ ] Sample insert + query by `as_of_date` range works
- [ ] Partition strategy documented for ops

### Technical Notes

- Retention policy documented: 7 years hot (TDS-006 §3.6)—automated prune is ops future work
- Prepare for PRICE_UPDATED / ARRIVAL_UPDATED events (E-03)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §3.6–3.7, [TDS-005](../tds/TDS-005-Event-Model.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_price_observation_append_only` | Insert two rows same market different as_of_date |
| `test_partition_pruning_explain` | EXPLAIN shows partition constraint (optional integration) |

### Traceability

REQ-031, REQ-070 | NFR-AUD-002 | TDS-005

---

## E-01-S05 — StructuredSignal and SignalSnapshot

### Summary

Persist domain agent outputs and daily snapshot bundle for replay.

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S03 | Blocks (commodity, registry FK prep) |
| E-00-S08 | Blocks (signal contract types) |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Table `structured_signal` with UNIQUE (`commodity_id`, `as_of_date`, `agent_type`, `registry_id`) |
| AC-2 | Table `signal_snapshot` with `signal_ids` array/JSON, `snapshot_hash`, `data_quality_snapshot_id` nullable |
| AC-3 | UNIQUE (`commodity_id`, `as_of_date`, `registry_id`) on snapshot |
| AC-4 | `signal_components` JSON column on structured_signal |
| AC-5 | Repository method `get_snapshot(commodity_id, as_of_date, registry_id)` |

### Definition of Done

- [ ] Insert 6 signals + 1 snapshot for test commodity in integration test
- [ ] `snapshot_hash` deterministic for same inputs (prep REQ-103)

### Technical Notes

- `agent_type` values match `shared.domain.AgentType`
- Acreage stored in Weather signal `signal_components` (founder clarification, TDS-004)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §3.8–3.9, [TDS-004](../tds/TDS-004-Agent-Architecture.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_signal_unique_per_agent_day` | Duplicate agent+date fails |
| `test_snapshot_hash_stable` | Same signals → same hash |

### Traceability

REQ-060, REQ-061 | FD-013 | NFR-TRC-003

---

## E-01-S06 — Forecast, ForecastVersion, and Feature Store Tables

### Summary

Forecast identity + immutable version rows + feature_set / feature_vector per TDS-006 §3.10–3.11, §10.

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S05 | Blocks (snapshot_id FK) |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Tables `forecast`, `forecast_version` per TDS-006 §3.10–3.11 |
| AC-2 | `horizon_30`, `horizon_60`, `horizon_90` as JSONB with point, band_low, band_high, direction, **forecast_confidence** |
| AC-3 | UNIQUE (`commodity_id`, `as_of_date`, `model_version`, `registry_id`) on forecast_version |
| AC-4 | Tables `feature_set`, `feature_vector` per TDS-006 §10 |
| AC-5 | `is_published` boolean; status enum: complete, failed, partial |

### Definition of Done

- [ ] Insert ForecastVersion linked to snapshot in integration test
- [ ] Repository rejects UPDATE on numeric horizon fields

### Technical Notes

- **forecast_confidence** per horizon stored here—not recommendation confidence (TDS-009 §7)
- Partition `forecast_version` by `as_of_date` monthly (TDS-006 §9)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md), [TDS-007](../tds/TDS-007-Forecast-Architecture.md), [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) §7.1

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_forecast_version_immutable` | Update point forecast blocked |
| `test_forecast_confidence_bounds` | confidence must be in [0,1] |

### Traceability

REQ-056, REQ-076 | FD-006, FD-014 | NFR-REP-001

---

## E-01-S07 — Decision Session Stack (UserContext through Outcome)

### Summary

Tables for per-position decision flywheel per TDS-006 §3.12–3.16.

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S06 | Blocks (forecast_version_id FK) |
| E-01-S03 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Tables: `user_context`, `decision_session`, `recommendation`, `recommendation_version`, `outcome` |
| AC-2 | `user_context`: persona_type enum farmer/trader only Phase 1; financing_profile JSON; liquidity_need enum |
| AC-3 | `recommendation_version`: action_type enum; **recommendation_confidence** field separate from forecast; `partial_quantity_pct`; `decision_trace` JSONB; `rules_applied` array |
| AC-4 | `decision_session` links: context_id, forecast_version_id, snapshot_id, registry_id, mi_snapshot_ref, explanation_id nullable |
| AC-5 | `outcome`: UNIQUE session_id; validation_status pending/validated/rejected |

### Definition of Done

- [ ] End-to-end insert: context → session → recommendation_version in test
- [ ] `recommendation_confidence` column exists and documented vs forecast_confidence (TDS-009)

### Technical Notes

- `msp_proximity_triggered` boolean on recommendation_version (FD-008, ±3%)
- `formula_version` string on recommendation_version
- No portfolio entity—one context per session (per-position trader)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §3.12–3.16, [TDS-008](../tds/TDS-008-Decision-Engine.md), [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) §7.2

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_decision_session_fk_chain` | Full FK chain valid |
| `test_one_outcome_per_session` | Second outcome insert fails |
| `test_action_type_enum` | Invalid action rejected |

### Traceability

REQ-040, REQ-041, REQ-090, REQ-110 | FD-015, FD-016, FD-023

---

## E-01-S08 — DataQualitySnapshot Table

### Summary

Per-refresh source health record per TDS-006 §3.17 and TDS-011.

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S03 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Table `data_quality_snapshot` with UNIQUE (`commodity_id`, `as_of_date`, `registry_id`) |
| AC-2 | Columns: `source_health` JSONB, `overall_quality_score`, `agmarknet_lag_hours`, `futures_feed_ok`, `signals_missing` array, `confidence_penalty_factor` |
| AC-3 | Optional FK from signal_snapshot to quality snapshot |
| AC-4 | Retention documented: 2 years (TDS-006) |

### Definition of Done

- [ ] Linked insert with snapshot in integration test
- [ ] Repository read by (commodity_id, as_of_date)

### Technical Notes

- Used by MI Framework and TrustAdj (TDS-008, TDS-011)—data only in this story
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §3.17, [TDS-011](../tds/TDS-011-Calibration-Architecture.md) §10

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_quality_score_bounds` | overall_quality_score in [0,1] |

### Traceability

REQ-084 | NFR-TRS-001 | TDS-011

---

## E-01-S09 — Redis MI Projection Client

### Summary

Redis client wrapper and key convention for MI snapshot cache per TDS-006 §4 and TDS-009 §8.

### Dependencies

| Dependency | Type |
|------------|------|
| E-00-S06 | Blocks (Redis) |
| E-01-S06 | Blocks (conceptual payload shape) |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Key pattern: `mi:{commodity_id}:{as_of_date}` documented and implemented |
| AC-2 | `set_mi_snapshot(key, payload, ttl)` and `get_mi_snapshot(key)` with JSON serialization |
| AC-3 | Default TTL 48h (TDS-006 §4) configurable via env |
| AC-4 | Redis is cache only—PostgreSQL remains source of truth |
| AC-5 | Graceful degrade if Redis unavailable (read returns miss, no crash on health) |

### Definition of Done

- [ ] Round-trip test with docker Redis
- [ ] Documented in backend README

### Technical Notes

- Payload shape aligns with TDS-009 MI Snapshot field groups (may be partial until E-05)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §4, [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) §8, FD-012

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_redis_mi_roundtrip` | Integration with fakeredis or compose |
| `test_redis_key_format` | Key matches convention |

### Traceability

REQ-037 | FD-012 | NFR-SCL-001

---

## E-01-S10 — CommodityRegistry Table (Schema Only)

### Summary

Versioned registry table supporting `required_agents[]`, `optional_agents[]`, `signal_weights` per TDS-009 (E-02 populates).

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S03 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Table `commodity_registry` per TDS-006 §3.3 **plus** architecture review fields: `required_agents`, `optional_agents`, `signal_weights`, `regime_priority` (JSON/array) |
| AC-2 | Partial UNIQUE one `is_active=true` per `commodity_id` |
| AC-3 | `decision_rules` JSONB includes: `msp_proximity_pct`, `default_partial_sell_pct`, `formula_version` |
| AC-4 | `forecast_horizons` default [30,60,90] |
| AC-5 | Version semver string + `effective_from` / `effective_to` |

### Definition of Done

- [ ] Schema supports TDS-009 cotton YAML excerpt without migration change in E-02
- [ ] ADR-003 documents versioning rules

### Technical Notes

- Deprecate use of `minimum_agents` alone—use required/optional split (TDS-009 §4.1)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §3.3, [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) §11.1, [ADR-003](../adrs/ADR-003-commodity-registry-versioning.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_single_active_registry` | Two active rows for same commodity fails |
| `test_required_agents_json_schema` | Validation rejects empty required list |

### Traceability

REQ-073, REQ-074 | FD-022, FD-008 | TDS-009

---

## E-01-S11 — Data Foundation Integration Test Suite

### Summary

Integration tests verifying FK graph, immutability, and replay-oriented reads per TDS-006 §5.

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S04 through E-01-S10 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Test fixture creates: commodity (test id), registry row, region, market, observations, 6 signals, snapshot, forecast_version |
| AC-2 | Test verifies historical read by `as_of_date` cutoff (no future observation visible) |
| AC-3 | Test documents replay hash inputs: registry_id + snapshot_hash + formula_version |
| AC-4 | All integration tests run in CI with Postgres service |
| AC-5 | Coverage report for `backend/app/persistence/` ≥ 80% line |

### Definition of Done

- [ ] CI green with integration job
- [ ] Serves as regression gate for E-02+ migrations

### Technical Notes

- Use test commodity id `cotton_test` to avoid colliding with E-02 seed `cotton`
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §5, REQ-103 (prep)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_full_fk_graph_fixture` | Mandatory |
| `test_as_of_date_cutoff` | Mandatory |
| CI | Integration job on PR |

### Traceability

REQ-090, REQ-103 | NFR-TRC-001 | TDS-006 §5

---

## Epic E-01 Definition of Done

| Gate | Condition |
|------|-----------|
| M1 data layer | All E-01 stories Done |
| Migrations | `alembic upgrade head` on empty DB creates full schema |
| Immutability | ForecastVersion / RecommendationVersion update guards proven |
| Redis | MI key contract implemented |
| E-02 unblocked | CommodityRegistry table ready for seed |

## Epic Dependencies

| Epic | Relationship |
|------|--------------|
| E-00 | Required |
| E-02 | Blocked until E-01-S03, E-01-S10 complete |

## Open Questions (Epic Level)

| ID | Item |
|----|------|
| OQ-004 | `stability_token` schema on recommendation_version |
| OQ-007 | Outcome validation_status workflow |

## Founder / Architecture Approvals

| Item | Status |
|------|--------|
| TDS-006 entity model | Frozen |
| required_agents / optional_agents | Architecture review (implemented E-01-S10) |
| InventoryPosition deferred | Architecture review (not in E-01) |
