# Agmarknet Ingestion Spike Report — PI5 Track B (E-03)

**Date:** 2026-06-04  
**PI:** PI5 Track B (KDO — non-production spike)  
**HEAD:** `faf3e66` @ `main`  
**Schema gate:** E-03 audit — `price_observation` / `arrival_observation` READY @ migration `0008`  
**E-02 seed:** Cotton + 4 Telangana mandis with `source_identifiers.agmarknet` ([`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json))

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Can OGD JSON be parsed deterministically? | **Yes** — `parse_ogd_response` / `parse_record`; `arrival_date` DD/MM/YYYY |
| Can OGD location triple → `market_id`? | **Yes** — 4/4 seeded Telangana mandis resolve via `AgmarknetMarketLookup` |
| Can commodity strings → `cotton`? | **Yes** — `Cotton`, `Kapas`, variants; **excludes** `Cotton Seed` |
| Can rows map to observation targets? | **Yes** — `PriceObservationDraft` / `ArrivalObservationDraft` align with E-01-S04 ORM |
| End-to-end mapping (fixture cotton)? | **PASS** — Khammam modal/min/max + arrival 42.5 t → 425 quintals |
| Production-ready ingest? | **No** — spike only; no scheduler, pipeline, or signal runtime |

---

## 2. Module Layout

| Path | Role |
|------|------|
| [`backend/app/services/ingest/agmarknet/constants.py`](../../backend/app/services/ingest/agmarknet/constants.py) | `SOURCE_AGMARKNET`, cotton label sets, unit defaults |
| [`backend/app/services/ingest/agmarknet/parser.py`](../../backend/app/services/ingest/agmarknet/parser.py) | OGD envelope + row parsing → `AgmarknetRecord` |
| [`backend/app/services/ingest/agmarknet/market_lookup.py`](../../backend/app/services/ingest/agmarknet/market_lookup.py) | `(state, district, market)` → `market_id` from E-02 seed |
| [`backend/app/services/ingest/agmarknet/mapper.py`](../../backend/app/services/ingest/agmarknet/mapper.py) | Records → price/arrival observation drafts |
| [`tests/fixtures/agmarknet/ogd_telangana_sample.json`](../../tests/fixtures/agmarknet/ogd_telangana_sample.json) | Fixture envelope (cotton + kapas + maize + arrival row) |
| [`tests/unit/test_agmarknet_ingest.py`](../../tests/unit/test_agmarknet_ingest.py) | Parser, mapper, lookup unit tests; optional DB integration |

**Explicitly not added:** scheduler jobs, production ingest pipeline, signal engine hooks.

---

## 3. Mapping Contract (OGD → Observations)

### 3.1 Market resolution

```
OGD (state, district, market) ──normalize──► AgmarknetMarketKey
                                              └──► market.source_identifiers.agmarknet
                                                   └──► market_id
```

| OGD triple | `market_id` |
|------------|-------------|
| Telangana / Khammam / Khammam | `mkt_tg_khammam_apmc` |
| Telangana / Warangal / Warangal | `mkt_tg_warangal` |
| Telangana / Karimnagar / Karimnagar | `mkt_tg_karimnagar` |
| Telangana / Khammam / Kesamudram | `mkt_tg_kesamudram` |

Unknown triples or non-cotton commodities produce **no drafts** (drop, not error).

### 3.2 Commodity resolution

| OGD `commodity` | `commodity_id` |
|-----------------|----------------|
| Cotton, Kapas, Cotton (Unginned), Cotton-Bags, Cotton-Loose | `cotton` |
| Cotton Seed | *(excluded)* |
| Other (e.g. Maize) | *(dropped)* |

### 3.3 Price observations

| OGD field | Draft / ORM |
|-----------|-------------|
| `modal_price` | `price_type=modal`, `value` |
| `min_price` / `max_price` | optional sibling rows |
| `arrival_date` | `as_of_date` (parsed date) |
| `variety` + `grade` | `quality_grade` (`variety\|grade`) |
| — | `unit=quintal`, `currency=INR`, `source=agmarknet` |
| — | `validation_status=received` |

### 3.4 Arrival observations

| OGD / portal field | Transform | Target |
|--------------------|-----------|--------|
| `arrival_tonnes` or `arrival` | × 10 | `volume` in quintals |
| `arrival_date` | parse | `as_of_date` |

OGD JSON API metadata often omits arrival volume; spike accepts portal-shaped rows per [AGMARKNET_DATA_PROOF.md](../research/AGMARKNET_DATA_PROOF.md) §5.5.

---

## 4. Fixture Proof (Khammam Cotton)

Source shape from [AGMARKNET_DATA_PROOF.md](../research/AGMARKNET_DATA_PROOF.md) §5.2 / §7.1:

```json
{
  "state": "Telangana",
  "district": "Khammam",
  "market": "Khammam",
  "commodity": "Cotton",
  "variety": "Cotton",
  "grade": "FAQ",
  "arrival_date": "26/03/2022",
  "min_price": 9000,
  "max_price": 12001,
  "modal_price": 10500
}
```

**Mapped drafts (logical):**

| Target | Key fields |
|--------|------------|
| `price_observation` (modal) | `mkt_tg_khammam_apmc`, `cotton`, `10500`, `2022-03-26`, `agmarknet` |
| `price_observation` (min/max) | `9000` / `12001` |
| `arrival_observation` | `425` quintals from `42.5` tonnes (companion fixture row) |

---

## 5. Test Summary

| Suite | Count | Notes |
|-------|-------|-------|
| `tests/unit/test_agmarknet_ingest.py` | **12** | 11 unit + 1 `@pytest.mark.integration` (skipped without `DATABASE_URL`) |

**Commands run @ spike:**

```bash
ruff check backend/app/services/ingest/ tests/unit/test_agmarknet_ingest.py
ruff format --check backend/app/services/ingest/ tests/unit/test_agmarknet_ingest.py
mypy backend/app/services/ingest/
pytest tests/unit/test_agmarknet_ingest.py -q
```

---

## 6. Gaps for E-03 Production

| Gap | Owner |
|-----|-------|
| Registered OGD `api-key` (demo slice has no cotton) | E-03 ops |
| 90-day `market` spelling audit (Warangal canonical name) | E-02-S02 |
| Arrival volume channel (zip/portal vs JSON API) | E-03 ingest spec |
| Idempotent upsert / `supersedes_id` job | E-03 pipeline |
| `data_quality_snapshot.agmarknet_lag_hours` | E-03 + E-01-S08 |

---

## 7. References

| Doc | Role |
|-----|------|
| [AGMARKNET_DATA_PROOF.md](../research/AGMARKNET_DATA_PROOF.md) | Payload samples + mapping §6–7 |
| [AGMARKNET_INGESTION_SPIKE.md](../research/AGMARKNET_INGESTION_SPIKE.md) | PI2 research spike |
| [E02_COMPLETION_REPORT.md](./E02_COMPLETION_REPORT.md) | Seed `source_identifiers` |
| [`observation.py`](../../backend/app/persistence/models/observation.py) | ORM targets |

---

*End of PI5 Track B Agmarknet ingestion spike.*
