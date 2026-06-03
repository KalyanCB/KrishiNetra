# E-01 Next Phase Readiness — S04 through S07

**Workstream:** E-01 KDO Workstream D (documentation)  
**Epic:** E-01 — Data Foundation  
**Scope:** Implementation readiness for **E-01-S04**, **S05**, **S06**, **S07** only  
**Date:** 2026-06-03  
**Authoritative sources:** [E-01-Data-Foundation.md](../stories/E-01-Data-Foundation.md), [E01_EXECUTION_PLAN.md](./E01_EXECUTION_PLAN.md), [TDS-006](../tds/TDS-006-Data-Model.md) §3.6–3.16, §4, §5, §9–§10, [ADR-002](../adrs/ADR-002-schema-migrations-alembic.md)

**Prerequisite gate (not in this phase):** E-01-S01 (Alembic), S02 (repositories), S03 (reference entities), **S10** (`commodity_registry`), **S08** (`data_quality_snapshot`) per [E01_EXECUTION_PLAN.md](./E01_EXECUTION_PLAN.md) §5 — migrations `0002`–`0004` and `0001` bootstrap must be applied before S04 DDL.

**Explicitly out of scope:** Cotton seed (E-02), `InventoryPosition` (E-12), automated retention prune, E-03 event emission, business services beyond persistence.

---

## Phase Context

| Story | Feature | Alembic rev (planned) | Partition (TDS-006 §9) |
|-------|---------|----------------------|--------------------------|
| E-01-S04 | F-01-02 Observation TS | `0005_observations_partitioned` | `price_observation`, `arrival_observation` — RANGE monthly on `as_of_date` + DEFAULT |
| E-01-S05 | F-01-03 SignalSnapshot | `0006_signals_partitioned` | `structured_signal` — RANGE monthly on `as_of_date`; `signal_snapshot` **not** listed in §9 (single row per commodity/day) |
| E-01-S06 | F-01-04 ForecastVersion + feature store | `0007_forecast_and_features` | `forecast_version` — RANGE monthly on `as_of_date` |
| E-01-S07 | F-01-05 Decision stack | `0008_decision_stack` | `decision_session` — RANGE **quarterly** on `created_at` |

**Critical path through this phase:** S03 → S10 → S08 → **S04** (parallel OK) → **S05** → **S06** → **S07** → S11.

---

## E-01-S04 — PriceObservation and ArrivalObservation (Time-Series)

### Dependencies

| Dependency | Type | Readiness note |
|------------|------|----------------|
| E-01-S03 | **Blocks** | `market_id`, `commodity_id` FKs; empty `market` rows sufficient for integration tests |
| E-01-S01 | **Blocks** (transitive) | Alembic rev chain; `Numeric` for prices, `DATE` for `as_of_date` (TDS-013 §5.2) |
| E-01-S02 | **Soft** | Append-only repository pattern should be used; no immutability guard like version tables |
| E-01-S10 | **Soft** | Observations do not FK to `registry_id`; ingest may later scope by commodity |
| E-03 | **Downstream** | PRICE_UPDATED / ARRIVAL_UPDATED events prepared in technical notes — no emitter in S04 |

S04 does **not** depend on S05, S06, S07, S08, or S09. It **can run in parallel** with S10/S08 after S03 if migration PRs are serialized (ADR-002 single `head`).

### Migration impacts

| Object | Action | Notes |
|--------|--------|-------|
| `price_observation` | CREATE partitioned table | All attributes per TDS-006 §3.6 |
| `arrival_observation` | CREATE partitioned table | TDS-006 §3.7 |
| `validation_status` enum | CREATE | `received`, `validated`, `published`, `superseded` (story AC-5) |
| `supersedes_id` | Self-FK nullable | Lineage chain; no UPDATE of superseded row semantics in E-01 |
| Partition children | CREATE initial month + **DEFAULT** partition | Story AC-3; DEFAULT catches rows outside declared ranges |
| Indexes | CREATE on parent (propagate to partitions) | See Index strategy |

**Revision:** `0005_observations_partitioned` — must run **after** `0002` (markets). **Reversible** per epic policy (ADR-002 §3).

**Ops consequence (ADR-002):** Each new calendar month needs a forward migration (or scripted ops step) to attach a RANGE child; document in story DoD ops runbook — not automated in E-01.

### Index strategy

| Table | Index | Purpose | TDS-006 trace |
|-------|-------|---------|---------------|
| `price_observation` | PK `observation_id` | Row identity | §3.6 |
| `price_observation` | `(commodity_id, as_of_date DESC)` | Backtest / commodity-wide range scans | §3.6, story AC-2 |
| `price_observation` | `(market_id, observed_at DESC)` | Latest price by market | §3.6, story AC-2 |
| `price_observation` | `(source, as_of_date)` | Ingest reconciliation (TDS-006 §3.6) | Optional but specified in TDS |
| `arrival_observation` | PK `observation_id` | Row identity | §3.7 |
| `arrival_observation` | `(commodity_id, as_of_date DESC)` | Range queries | §3.7, story AC-2 |
| `arrival_observation` | `(market_id, observed_at DESC)` | Latest by market | §3.7, story AC-2 |

**Design notes:** Prefer indexes that align with partition key `as_of_date` so planner can prune partitions on date-range filters. `observed_at` index supports replay cutoff (TDS-006 §5 step 2: `observed_at <= end_of_as_of_date`).

### Partitioning concerns

| Concern | Detail | Mitigation |
|---------|--------|------------|
| Monthly RANGE on `as_of_date` | TDS-006 §4, §9; ADR-002 §5 | Initial partition for current month + DEFAULT |
| DEFAULT partition | Required by story AC-3 | Prevents insert failures before ops adds next month |
| High ingest volume | DM2-004: monthly sufficient Phase 1 | Monitor; finer daily partitions deferred |
| 7-year hot retention | TDS-006 §3.6; story notes | Document only — automated prune is future ops (R-B-11) |
| Cross-partition uniqueness | PK is UUID global | No UNIQUE across `(market_id, as_of_date)` unless added later — supersede via `supersedes_id` |
| `EXPLAIN` partition pruning | Story optional test | CI integration with `test_partition_pruning_explain` |

**Pruning (§9):** Observations hot **7 years**; implementation does not drop partitions in E-01.

### Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| S04-R1 | Missing market FK / wrong `Numeric` scale | High | Gate on S03 integration tests |
| S04-R2 | Forgetting DEFAULT partition | High | AC-3; migration review checklist |
| S04-R3 | Partition child drift at month boundary | Medium | Ops runbook in DoD; calendar migration playbook (R-B-03) |
| S04-R4 | Float prices instead of `Numeric` | Medium | S01 technical notes; breaks money semantics |
| S04-R5 | Concurrent Alembic heads if S04 parallel with S08/S10 | Medium | Serialize migration PRs (R-B-04) |
| S04-R6 | Supersede chain integrity | Low | Nullable `supersedes_id`; validation in ingest (E-03) |

### Test strategy

| Test | Type | AC / trace |
|------|------|------------|
| `test_price_observation_append_only` | Integration | Insert two rows, same market, different `as_of_date` — AC-1 |
| `test_partition_pruning_explain` | Integration (optional) | `EXPLAIN` shows partition constraint on `as_of_date` range |
| Sample range query | Manual / integration | DoD: query by `as_of_date` range |
| Migration up/down | Integration | Reversible migration on ephemeral Postgres (S01 CI pattern) |
| FK to `market` | Integration | Invalid `market_id` rejected |

**CI:** Run with Postgres service container after S01 AC-5 pattern. No Redis.

---

## E-01-S05 — StructuredSignal and SignalSnapshot

### Dependencies

| Dependency | Type | Readiness note |
|------------|------|----------------|
| E-01-S03 | **Blocks** | `commodity_id` FK |
| E-01-S10 | **Blocks** (effective) | `registry_id` FK to `commodity_registry` — rev `0003` before `0006` |
| E-01-S08 | **Blocks** (ordering) | `data_quality_snapshot_id` nullable FK on `signal_snapshot` — S08 before S05 per execution plan §5 |
| E-00-S08 | **Blocks** | `shared.domain.AgentType` for `structured_signal.agent_type` (R-B-02) |
| E-01-S02 | **Soft** | `get_snapshot(commodity_id, as_of_date, registry_id)` repository method (AC-5) |
| E-01-S06 | **Downstream** | `snapshot_id` FK on `forecast_version` |

S05 does **not** depend on S04 (observations). Agents may reference `source_observation_refs[]` without observation rows in E-01 tests.

### Migration impacts

| Object | Action | Notes |
|--------|--------|-------|
| `structured_signal` | CREATE (+ partition if per §9) | UNIQUE (`commodity_id`, `as_of_date`, `agent_type`, `registry_id`) |
| `signal_snapshot` | CREATE | UNIQUE (`commodity_id`, `as_of_date`, `registry_id`); `signal_ids` array/JSON; `snapshot_hash` |
| `data_quality_snapshot_id` | FK nullable → `data_quality_snapshot` | S08 table must exist (rev `0004`) |
| `signal_components` | JSON column | Acreage in Weather signal per TDS-004 founder clarification |

**Revision:** `0006_signals_partitioned`.

**Partitioning alignment:** TDS-006 §9 partitions **`structured_signal`** only. `signal_snapshot` is replay-critical, low cardinality (one per commodity/day/registry) — implement as **non-partitioned** unless volume review dictates otherwise; do not partition unless ops requires it.

### Index strategy

| Table | Index | Purpose |
|-------|-------|---------|
| `structured_signal` | PK `signal_id` | Identity |
| `structured_signal` | UNIQUE (`commodity_id`, `as_of_date`, `agent_type`, `registry_id`) | One signal per agent per day (AC-1) |
| `structured_signal` | (`as_of_date` DESC) | TDS-006 §3.8 time-series access |
| `signal_snapshot` | PK `snapshot_id` | Identity |
| `signal_snapshot` | UNIQUE (`commodity_id`, `as_of_date`, `registry_id`) | AC-3 |
| `signal_snapshot` | GIN on `signal_ids` (optional) | TDS-006 §3.9 — enable if array containment queries needed |

### Partitioning concerns

| Concern | Detail | Mitigation |
|---------|--------|------------|
| Monthly RANGE on `structured_signal.as_of_date` | §9: 6 agents × daily | Same month-boundary playbook as S04 |
| `signal_snapshot` not in §9 table | One bundle per day | Keep unpartitioned; index UNIQUE suffices |
| 3-year retention (signals) | TDS-006 §3.8, §9 pruning note | Document; no automated drop in E-01 |
| `snapshot_hash` determinism | REQ-103 prep | Stable canonical serialization in repository (test required) |
| Six agents per snapshot | AC integration: 6 signals + 1 snapshot | Fixture uses all `AgentType` values from E-00-S08 |

### Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| S05-R1 | E-00-S08 incomplete — invalid `agent_type` | **High** (blocking) | Verify `test_enum_values_match_tds` green before S05 |
| S05-R2 | S08 not migrated before S06 rev | High | Enforce order S10 → S08 → S05 |
| S05-R3 | Non-deterministic `snapshot_hash` | Medium | Canonical JSON ordering; unit test `test_snapshot_hash_stable` |
| S05-R4 | Duplicate agent+day | Medium | UNIQUE constraint + `test_signal_unique_per_agent_day` |
| S05-R5 | Missing quality FK when quality row exists | Low | Nullable FK; integration links both in S11 |

### Test strategy

| Test | Type | AC / trace |
|------|------|------------|
| `test_signal_unique_per_agent_day` | Integration | Duplicate insert fails |
| `test_snapshot_hash_stable` | Unit | Same six signals → identical hash |
| Insert 6 signals + 1 snapshot | Integration | DoD |
| `get_snapshot(...)` | Unit/integration | Repository AC-5 |
| Partition pruning (structured_signal) | Integration (optional) | Same pattern as S04 if partitioned |

**CI:** Postgres required; no Redis. Enum values must match `shared.domain.AgentType`.

---

## E-01-S06 — Forecast, ForecastVersion, and Feature Store

### Dependencies

| Dependency | Type | Readiness note |
|------------|------|----------------|
| E-01-S05 | **Blocks** | `snapshot_id` FK on `forecast_version` |
| E-01-S03 | **Blocks** (transitive) | `commodity_id` on `forecast` |
| E-01-S10 | **Blocks** (transitive) | `registry_id` on `forecast_version` |
| E-01-S02 | **Blocks** (pattern) | Insert-only repository; no UPDATE on published numeric horizons (TDS-006 §6) |
| E-01-S07 | **Downstream** | `forecast_version_id` on `decision_session` |
| E-01-S09 | **Soft** | Redis MI payload shape references forecast fields — after S06 |

### Migration impacts

| Object | Action | Notes |
|--------|--------|-------|
| `forecast` | CREATE | Logical identity; `commodity_id`, `created_at` |
| `forecast_version` | CREATE partitioned | Immutable version rows |
| `feature_set` | CREATE | TDS-006 §10 metadata |
| `feature_vector` | CREATE | (`feature_set_id`, `feature_name`) |
| `horizon_30/60/90` | JSONB | point, band_low, band_high, direction, **forecast_confidence** per horizon |
| `status` enum | CREATE | `complete`, `failed`, `partial` |
| `is_published` | boolean | TDS-006 §6 publishing rules |

**Revision:** `0007_forecast_and_features`.

**Immutability:** Repository must reject UPDATE on published numeric horizon fields (story DoD; S02 pattern). New model run = new INSERT.

### Index strategy

| Table | Index | Purpose |
|-------|-------|---------|
| `forecast` | PK `forecast_id` | §3.10 |
| `forecast_version` | PK `forecast_version_id` | §3.11 |
| `forecast_version` | UNIQUE (`commodity_id`, `as_of_date`, `model_version`, `registry_id`) | AC-3 |
| `forecast_version` | (`as_of_date` DESC, `is_published`) | Latest published lookup |
| `forecast_version` | (`snapshot_id`) | Replay join to snapshot |
| `feature_set` | PK `feature_set_id` | §10 |
| `feature_vector` | (`feature_set_id`, `feature_name`) | Feature lookup |

### Partitioning concerns

| Concern | Detail | Mitigation |
|---------|--------|------------|
| Monthly RANGE on `forecast_version.as_of_date` | §9 | Same ops playbook as observations |
| All versions retained indefinitely | §3.11 | Partitioning for query performance, not aggressive prune |
| `feature_set` / `feature_vector` | Not in §9 | Unpartitioned; link via `ForecastVersion.feature_set_ref` |
| One `is_published` per (commodity, as_of_date) | TDS-006 §6 | Enforce in service layer Phase 1; optional partial unique index deferred |
| `forecast_confidence` vs recommendation | TDS-009 §7 | **Only** on horizon JSON here — not `recommendation_confidence` (S07) |

### Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| S06-R1 | UPDATE on published horizons | High | Repository guard + `test_forecast_version_immutable` |
| S06-R2 | Confidence outside [0,1] | Medium | Check constraint or repo validation + `test_forecast_confidence_bounds` |
| S06-R3 | JSONB schema drift across horizons | Medium | Pydantic model shared with API prep (TDS-007) |
| S06-R4 | Missing snapshot FK | High | Integration test links real `snapshot_id` from S05 fixture |
| S06-R5 | Conflating forecast and recommendation confidence | Medium | Code review; document in S07 |
| S06-R6 | Partition month drift | Medium | Shared ops runbook with S04 |

### Test strategy

| Test | Type | AC / trace |
|------|------|------------|
| `test_forecast_version_immutable` | Unit | UPDATE blocked on numeric fields |
| `test_forecast_confidence_bounds` | Unit | Values in [0,1] |
| Insert ForecastVersion + snapshot | Integration | DoD |
| S02 stub extension | Unit | Reuse insert-only pattern from S02 before S06 if stub existed |
| Feature set linkage | Integration | `feature_set_ref` populated on version row |

**CI:** Postgres; coverage toward S11 ≥80% on `backend/app/persistence/`.

---

## E-01-S07 — Decision Session Stack (UserContext through Outcome)

### Dependencies

| Dependency | Type | Readiness note |
|------------|------|----------------|
| E-01-S06 | **Blocks** | `forecast_version_id` FK on `decision_session` |
| E-01-S05 | **Blocks** (transitive) | `snapshot_id` on session |
| E-01-S03 | **Blocks** | `commodity_id` context |
| E-01-S10 | **Blocks** (transitive) | `registry_id` on session |
| E-01-S02 | **Blocks** (pattern) | `recommendation_version` insert-only immutability |
| TDS-008 / TDS-009 | **Reference** | `action_type`, MSP proximity, formula_version — schema only in E-01 |

No dependency on S04, S08, or S09 for DDL. S08 quality optional on session (`mi_snapshot_ref` is ref string, not necessarily DQ FK).

### Migration impacts

| Object | Action | Notes |
|--------|--------|-------|
| `user_context` | CREATE | `persona_type` enum `farmer`/`trader` Phase 1 only |
| `decision_session` | CREATE partitioned (quarterly `created_at`) | Links context, forecast, snapshot, registry |
| `recommendation` | CREATE | Session-scoped logical id |
| `recommendation_version` | CREATE | `recommendation_confidence` **separate** from forecast confidence |
| `outcome` | CREATE | UNIQUE (`session_id`); `validation_status` enum |
| Enums | CREATE | `action_type`, `liquidity_need`, `validation_status`, etc. per story AC |

**Revision:** `0008_decision_stack` — final business tables before S09/S11.

**Open questions (epic):** OQ-004 `stability_token` — nullable/JSON placeholder; OQ-007 outcome workflow — enum only, no state machine in E-01.

### Index strategy

| Table | Index | Purpose |
|-------|-------|---------|
| `user_context` | PK `context_id` | §3.12 |
| `user_context` | (`persona_type`, `captured_at` DESC) | Analytics |
| `decision_session` | PK `session_id` | §3.13 |
| `decision_session` | (`commodity_id`, `as_of_date` DESC) | Session lookup |
| `decision_session` | (`context_id`) | 1:1 context binding |
| `decision_session` | (`status`, `created_at`) | Ops queries |
| `recommendation` | PK; UNIQUE (`session_id`) | One recommendation per session |
| `recommendation_version` | PK; (`recommendation_id`, `version`) | Version chain |
| `recommendation_version` | (`action_type`, `created_at`) | Reporting |
| `outcome` | PK; UNIQUE (`session_id`) | One outcome per session (AC) |

### Partitioning concerns

| Concern | Detail | Mitigation |
|---------|--------|------------|
| `decision_session` quarterly RANGE on `created_at` | TDS-006 §9 — lower volume than observations | Initial quarter partition + DEFAULT |
| Other decision tables | Not in §9 | Unpartitioned |
| 5-year retention | §3.12–3.13 | Document; no prune in E-01 |
| `as_of_date` on session vs `created_at` partition key | Query by business date vs insert time | Indexes on `as_of_date`; partition on `created_at` per TDS — document for ops |
| No portfolio entity | Founder clarification | One `user_context` per session |

### Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| S07-R1 | Broken FK chain | High | `test_decision_session_fk_chain` end-to-end |
| S07-R2 | Second outcome row | Medium | UNIQUE + `test_one_outcome_per_session` |
| S07-R3 | `recommendation_confidence` conflated with `forecast_confidence` | High | Separate columns; document TDS-009 §7 in DoD |
| S07-R4 | Invalid `action_type` | Medium | Enum + `test_action_type_enum` |
| S07-R5 | OQ-004 / OQ-007 scope creep | Low | Placeholder columns only |
| S07-R6 | Quarterly partition boundary | Low | Ops runbook (same family as monthly) |

### Test strategy

| Test | Type | AC / trace |
|------|------|------------|
| `test_decision_session_fk_chain` | Integration | context → session → recommendation_version |
| `test_one_outcome_per_session` | Integration | Second outcome fails |
| `test_action_type_enum` | Unit/integration | Invalid action rejected |
| Immutability | Unit | RecommendationVersion UPDATE blocked (S02 pattern) |
| `recommendation_confidence` present | Integration / doc | DoD column exists, documented vs forecast |
| Full stack fixture | Integration | Feeds S11 `test_full_fk_graph_fixture` |

**CI:** Postgres; full FK graph is mandatory S11 gate.

---

## Cross-Story Concerns (S04–S07)

### Migration sequencing summary

```
0002_reference_entities (S03)
  → 0003_commodity_registry (S10)
  → 0004_data_quality_snapshot (S08)
  → 0005_observations_partitioned (S04)  [parallel safe if single head]
  → 0006_signals_partitioned (S05)
  → 0007_forecast_and_features (S06)
  → 0008_decision_stack (S07)
```

### Partitioning playbook (TDS-006 §9 + ADR-002)

| Table | Key | Granularity | Story | Retention (hot) |
|-------|-----|-------------|-------|-----------------|
| `price_observation` | `as_of_date` | Monthly + DEFAULT | S04 | 7 years |
| `arrival_observation` | `as_of_date` | Monthly + DEFAULT | S04 | 7 years |
| `structured_signal` | `as_of_date` | Monthly | S05 | 3 years |
| `forecast_version` | `as_of_date` | Monthly | S06 | Indefinite (all versions) |
| `decision_session` | `created_at` | Quarterly | S07 | 5 years min |

**Shared ops requirements:** Document manual child-partition creation; no automated prune in E-01 (R-B-11).

### Replay readiness (TDS-006 §5)

| Step | S04–S07 data |
|------|----------------|
| 2 | Observations: `observed_at <= end_of_as_of_date` — S04 tests seed cutoff behavior for S11 |
| 3 | `signal_snapshot` + hash — S05 |
| 4 | `forecast_version` with `snapshot_id`, `model_version` — S06 |
| 5 | `user_context` + `recommendation_version` with `formula_version` — S07 |

S11 will verify `registry_id` + `snapshot_hash` + `formula_version` replay inputs.

### Global risks (from execution plan §8)

| ID | Applies to | Note |
|----|------------|------|
| R-B-02 | S05 | E-00-S08 blocking |
| R-B-03 | S04, S05, S06, S07 | Partition child drift |
| R-B-04 | S04 parallel tranche | Single Alembic head |
| R-B-06 | S07 | OQ-004 stability_token |
| R-B-07 | S07 | OQ-007 outcome workflow |

---

## Readiness Verdict

| Story | Doc ready | Implementation ready when |
|-------|-----------|----------------------------|
| E-01-S04 | **Yes** | S03 + S01/S02 complete; rev `0005` |
| E-01-S05 | **Yes** | S03, S10, S08, **E-00-S08** complete; rev `0006` |
| E-01-S06 | **Yes** | S05 complete; rev `0007` |
| E-01-S07 | **Yes** | S06 complete; rev `0008` |

**Program gate:** E-00 M0 complete (especially S06 Postgres/Redis, S08 shared contracts) before first S04 migration PR.

---

## References

| Document | Use |
|----------|-----|
| [E01_EXECUTION_PLAN.md](./E01_EXECUTION_PLAN.md) | Migration order, risks, test matrix |
| [TDS-006](../tds/TDS-006-Data-Model.md) | Entities §3.6–3.16; TS §4; replay §5; partitions §9; features §10 |
| [ADR-002](../adrs/ADR-002-schema-migrations-alembic.md) | Alembic, partitioning, immutability |
| [TDS-005](../tds/TDS-005-Event-Model.md) | Observation event prep (S04) |
| [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) | Confidence separation §7 |

---

*End of E-01 S04–S07 next phase readiness — Workstream D deliverable.*
