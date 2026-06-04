# Observation Population Report — PI5 Track C (E-03)

**Date:** 2026-06-04  
**PI:** PI5 Track C (KDO — Cotton + Telangana population proof)  
**HEAD:** `faf3e66` @ `main`  
**Schema gate:** `alembic_version` = `0008_decision_stack`  
**Upstream:** PI5 Track B Agmarknet spike ([`AGMARKNET_SPIKE_REPORT.md`](AGMARKNET_SPIKE_REPORT.md))

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Can OGD fixture rows persist as real DB observations? | **Yes** — 7 price + 1 arrival rows inserted |
| Cotton + Telangana FK chain valid? | **Yes** — `commodity_id=cotton`, markets `mkt_tg_khammam_apmc`, `mkt_tg_warangal` |
| Repositories used (append-only)? | **Yes** — `PriceObservationRepository` / `ArrivalObservationRepository` |
| Integration tests (DATABASE_URL)? | **PASS** — `tests/integration/test_observation_population.py` |
| Unit tests (mapper/parser)? | **PASS** — 11 tests in `tests/unit/test_agmarknet_ingest.py` |
| Production ingest? | **No** — proof script + spike module only; no scheduler or signal runtime |

**Overall:** **PASS**

---

## 2. Prerequisites

| Step | Command / artifact | Result |
|------|-------------------|--------|
| Postgres @ head | `DATABASE_URL=…@127.0.0.1:5433/krishinetra` + `uv run alembic upgrade head` | `0008_decision_stack` |
| Cotton seed | `uv run python scripts/seed_cotton_baseline.py` | Idempotent apply |
| Fixture | [`tests/fixtures/agmarknet/ogd_telangana_sample.json`](../../tests/fixtures/agmarknet/ogd_telangana_sample.json) | 4 OGD records |

**Note:** Host `.env` may point at port `5432`; integration gate uses **`kn-test-pg` @ `127.0.0.1:5433`**.

---

## 3. Record Counts (Before / After)

Population run: `uv run python scripts/observation_population_proof.py` with `DATABASE_URL` @ 5433.

| Metric | Before | Inserted | After |
|--------|--------|----------|-------|
| `price_observation` (cotton, `source=agmarknet`) | 0 | 7 | 7 |
| `arrival_observation` (cotton, `source=agmarknet`) | 0 | 1 | 1 |
| **Total** | **0** | **8** | **8** |

| OGD envelope | Mapped drafts (cotton only) | Dropped |
|--------------|----------------------------|---------|
| 4 records | 7 price + 1 arrival | 1 row (Maize @ unknown mandi `Dharmapuri APMC`) |

---

## 4. Mapping Examples (Source → Persisted)

### 4.1 OGD row → price observations (Khammam Cotton FAQ)

| OGD field | Value | Persisted |
|-----------|-------|-----------|
| `state` / `district` / `market` | Telangana / Khammam / Khammam | `market_id=mkt_tg_khammam_apmc` |
| `commodity` | Cotton | `commodity_id=cotton` |
| `arrival_date` | 26/03/2022 | `as_of_date=2022-03-26` |
| `min_price` / `max_price` / `modal_price` | 9000 / 12001 / 10500 | 3 rows (`price_type` min/max/modal) |
| `variety` + `grade` | Cotton + FAQ | `quality_grade=Cotton\|FAQ` |

### 4.2 OGD row → arrival (42.5 tonnes → quintals)

| OGD field | Value | Persisted |
|-----------|-------|-----------|
| `arrival_tonnes` | 42.5 | `volume=425`, `unit=quintal` |
| `market` | Khammam | `market_id=mkt_tg_khammam_apmc` |
| `as_of_date` | 2022-03-26 | matches price row date |

### 4.3 Kapas → cotton (Warangal)

| OGD `commodity` | `market_id` | `as_of_date` | `modal` value |
|-----------------|-------------|--------------|---------------|
| Kapas | `mkt_tg_warangal` | 2026-06-04 | 10000 INR/quintal |

---

## 5. Sample Persisted Rows

Representative rows returned by the proof script (UUIDs vary per run).

### Price (`price_observation`)

| market_id | commodity_id | as_of_date | price_type | value | unit | validation_status |
|-----------|--------------|------------|------------|-------|------|-------------------|
| `mkt_tg_khammam_apmc` | `cotton` | 2022-03-26 | min | 9000.0000 | quintal | received |
| `mkt_tg_khammam_apmc` | `cotton` | 2022-03-26 | max | 12001.0000 | quintal | received |
| `mkt_tg_khammam_apmc` | `cotton` | 2022-03-26 | modal | 10500.0000 | quintal | received |
| `mkt_tg_warangal` | `cotton` | 2026-06-04 | modal | 10000.0000 | quintal | received |

### Arrival (`arrival_observation`)

| market_id | commodity_id | as_of_date | volume | unit | validation_status |
|-----------|--------------|------------|--------|------|-------------------|
| `mkt_tg_khammam_apmc` | `cotton` | 2022-03-26 | 425.0000 | quintal | received |

---

## 6. FK Validation Proof

After insert, `validate_fk_references` confirms:

1. `CommodityModel` row `cotton` exists (E-02 seed).
2. Every distinct `market_id` in drafts resolves to `MarketModel`:
   - `mkt_tg_khammam_apmc`
   - `mkt_tg_warangal`

Integration test additionally asserts:

- `PriceObservationModel` insert with `market_id=mkt_tg_khammam_apmc` and `commodity_id=cotton` succeeds.
- Invalid market FK still rejected (covered in `tests/unit/test_observations.py`).

Negative control: OGD Maize @ `Dharmapuri APMC` produces **zero drafts** (non-cotton + unmapped mandi).

---

## 7. Idempotency Note

| Layer | Behavior |
|-------|----------|
| **Cotton seed** (`SeedRunner.apply("cotton")`) | **Idempotent** — safe to re-run |
| **Observation insert** | **Append-only** — each run allocates new `observation_id` UUIDs; **no business-key dedupe** |
| **Re-run proof** | Second `run_population_proof` adds +7 price / +1 arrival (integration test asserts 14 price rows after two runs) |

Production ingest will need explicit dedupe or supersede policy (out of scope for Track C).

---

## 8. Module Layout

| Path | Role |
|------|------|
| [`backend/app/spike/agmarknet/population.py`](../../backend/app/spike/agmarknet/population.py) | Load fixture, map, persist, count, FK check |
| [`scripts/observation_population_proof.py`](../../scripts/observation_population_proof.py) | CLI JSON proof emitter |
| [`tests/integration/test_observation_population.py`](../../tests/integration/test_observation_population.py) | DB integration gate |
| Track B ingest | [`backend/app/services/ingest/agmarknet/`](../../backend/app/services/ingest/agmarknet/) |

**Explicitly not added:** scheduler, production pipeline, signal runtime.

---

## 9. Test & Quality Gate

```bash
export DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra
uv run pytest tests/integration/test_observation_population.py tests/unit/test_agmarknet_ingest.py -q
uv run ruff check backend/app/spike/agmarknet/ scripts/observation_population_proof.py
uv run mypy backend/app/spike/agmarknet/population.py scripts/observation_population_proof.py
```

| Gate | Result |
|------|--------|
| Integration + unit (14 tests) | **PASS** |
| `ruff` | **PASS** |
| `mypy` | **PASS** |

---

*End of PI5 Track C observation population report.*
