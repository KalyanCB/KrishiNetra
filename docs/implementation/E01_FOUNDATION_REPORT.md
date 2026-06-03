# E-01 Foundation Report — S01–S03 (PI1 Track A)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Scope** | E-01-S01, S02, S03 only (ADR-002, TDS-006 §3.1–3.5) |
| **HEAD** | `30583fc` |
| **Out of scope** | S04–S11, E-02 seed, cotton data |

---

## 1. Executive summary

Track A validates the **data foundation slice** delivered in Phase 1: Alembic bootstrap, repository immutability pattern, and reference-entity DDL/ORM. All three stories meet acceptance criteria at the **code and unit-test** level. **Integration tests** require `DATABASE_URL` (CI Postgres or local `docker-compose.dev.yml` + `.env`); local re-run on audit host failed Postgres authentication — treat CI as authoritative until dev stack is repaired.

**Verdict:** S01–S03 **complete** for PI1 stop rule. **Not** sufficient to close epic E-01.

---

## 2. E-01-S01 — Migration framework

### Deliverables

| Artifact | Location |
|----------|----------|
| Alembic root | `alembic.ini` → `backend/app/persistence/migrations/` |
| Environment | `migrations/env.py` (reads `DATABASE_URL` from settings) |
| Bootstrap revision | `0001_alembic_bootstrap.py` (no business tables) |
| Session factory | `backend/app/persistence/database.py` — `Base`, `SessionLocal`, `create_db_engine` |
| FastAPI dependency | `dependencies.get_db` |
| Documentation | `backend/app/persistence/README.md` (naming convention) |

### Acceptance criteria

| AC | Status | Evidence |
|----|--------|----------|
| AC-1 Alembic under persistence | **Met** | Directory tree present |
| AC-2 `upgrade head` on empty DB | **Met** (CI) | `.github/workflows/ci.yml` step; `test_alembic_upgrade_head` |
| AC-3 Base + session factory | **Met** | `database.py` |
| AC-4 Naming convention documented | **Met** | README + `0001`/`0002` slug pattern |
| AC-5 CI migrations on Postgres | **Met** | Service container + env `DATABASE_URL` |

### Tests

| Test | Type | Result (no local DB) |
|------|------|----------------------|
| `test_alembic_revision_chain` | Unit | Pass |
| `test_alembic_upgrade_head` | Integration | Skip |
| `test_alembic_downgrade_one_revision` | Integration | Skip |

---

## 3. E-01-S02 — Repository base pattern

### Deliverables

| Artifact | Purpose |
|----------|---------|
| `repositories/base.py` | `BaseRepository`, `ImmutableVersionRepository` |
| `shared/persistence/contracts.py` | `block_immutable_update`, `ImmutableVersionUpdateError` |
| `unit_of_work.py` | Transaction boundary helper |
| `REPOSITORY_PATTERN.md` | Append-only vs immutable vs versioned config |

### Acceptance criteria

| AC | Status | Evidence |
|----|--------|----------|
| AC-1 Pattern documented | **Met** | REPOSITORY_PATTERN.md (three repository classes) |
| AC-2 `get_by_id`, `insert`; no UPDATE on immutable | **Met** | `ImmutableVersionRepository.update` raises |
| AC-3 Unit of work | **Met** | `UnitOfWork` context manager |
| AC-4 Under `repositories/` | **Met** | `repositories/reference.py` stub |

### Tests

| Test | Result |
|------|--------|
| `test_repository_insert_only_forecast_version` | Pass (stub ORM model) |
| `test_persistence_session` | Pass |

**Note:** Immutability is proven on a **stub** table until E-01-S06 adds `forecast_version`.

---

## 4. E-01-S03 — Reference entities

### Deliverables

| Artifact | Purpose |
|----------|---------|
| `0002_reference_entities.py` | DDL: commodity, profile, region, market |
| `models/reference.py` | SQLAlchemy 2.x mapped models |
| `repositories/reference.py` | `CommodityRepository` (pattern stub) |
| `seeds/runner.py` | Fixture loader; `apply()` deferred to E-02 |

### Acceptance criteria

| AC | Status | Evidence |
|----|--------|----------|
| AC-1 Four tables per TDS-006 §3.1–3.5 | **Met** | Migration + models |
| AC-2 Indexes | **Met** | `ix_commodity_status_active` (partial), `ix_market_commodity_region`, `ix_region_commodity_type` |
| AC-3 Profile JSON columns | **Met** | Four JSONB fields on `commodity_profile` |
| AC-4 FK chain | **Met** | Migration constraints; integration tests |
| AC-5 Reversible | **Met** | `downgrade()` drops tables; downgrade test |

### Tests

| Test | AC | Result (no local DB) |
|------|-----|----------------------|
| `test_commodity_profile_fk` | Profile→commodity | Skip |
| `test_region_market_hierarchy` | Region→market | Skip |
| `test_market_requires_valid_region_fk` | FK enforce | Skip |
| `test_seed_framework` | Seed loader | Pass (unit) |

### Reference data policy

- **No cotton seed** in E-01 (per story) — correct.
- Empty tables after `upgrade head` — expected for E-02 bootstrap.

---

## 5. Migration chain

```text
0001_alembic_bootstrap  →  (no business tables)
0002_reference_entities →  commodity, commodity_profile, region, market
```

**Head:** `0002_reference_entities`  
**Planned next (not implemented):** `0003_commodity_registry` (S10), then S08/S04 per `E01_EXECUTION_PLAN.md`.

---

## 6. Validation evidence (2026-06-03)

| Check | Result |
|-------|--------|
| `uv run ruff check .` | Pass |
| `uv run mypy` | Pass |
| `uv run python scripts/check_imports.py` | Pass |
| `uv run pytest tests/ -v` | 28 passed, 6 skipped |
| `./scripts/ci-local.sh` | Pass (no `DATABASE_URL`) |
| Local `alembic upgrade head` | **Not run** — auth failure on 127.0.0.1:5432 |

**Recommendation before founder sign-off:** Copy `.env.example` → `.env`, run `./scripts/dev-up.sh`, export `DATABASE_URL`, then:

```bash
uv run alembic upgrade head
uv run pytest tests/integration/ -v
```

---

## 7. Gaps and risks (S01–S03 only)

| ID | Gap | Severity |
|----|-----|----------|
| F-01 | Integration tests skipped in default dev shell | Medium |
| F-02 | `SeedRunner.apply` not implemented | Low (E-02) |
| F-03 | Only `CommodityRepository` exists; region/market repos deferred | Low |
| F-04 | S10 `commodity_registry` blocks E-02 registry stories | **High** (program) |

---

## 8. ADR-002 compliance

| ADR-002 rule | S01–S03 |
|--------------|---------|
| Migrations in `backend/app/persistence/migrations/` | Yes |
| Forward migrations; dev downgrade | Yes (`0002` downgrade tested) |
| Immutable tables at repository layer | Pattern ready (S02); tables in S06+ |
| Monthly partitioning | N/A until S04/S06 |

---

## 9. Track A conclusion

| Story | Status |
|-------|--------|
| E-01-S01 | **Complete** |
| E-01-S02 | **Complete** |
| E-01-S03 | **Complete** |

Epic E-01 remains **in progress** (8 stories not started). Proceed to **E-01-S10** then **S04+** or E-02 docs-only per PI1 stop rule.
