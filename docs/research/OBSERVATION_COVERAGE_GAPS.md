# Observation Coverage Gaps — PI7 Track F

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI7 Track F (KDO — research only; no runtime code) |
| **Epic** | E-03 observation foundation → E-04 signal inputs |
| **Scope** | Cotton belt @ `127.0.0.1:5433` (`kn-test-pg`): market registry vs Agmarknet load, 36-month date density, NASA weather pairing, OGD ops blocker, DQS path to **>0.70** |
| **Out of scope** | Ingest implementation, signal runtime, dashboard UI |

---

## 1. PI7 state snapshot (@ 5433)

| Dimension | PI7 delivered | Observation reality |
|-----------|---------------|---------------------|
| **Markets seeded** | **27** Agmarknet mandis (5 states) | **2** with any price/arrival row after fixture backfill |
| **Telangana primary (E-03-S02 scope)** | **4** mandis | **2** reporting (`khammam_apmc`, `warangal`); **0** for Karimnagar, Kesamudram |
| **Belt markets without Agmarknet rows** | — | **25 / 27** (93%) — all MH, GJ, AP, KA + 6 extra TG mandis |
| **Historical window** | `2023-06-01` → `2026-06-03` (**1099** days) | **3** distinct `as_of_date` with price data (**0.27%** calendar completeness) |
| **Fixture backfill** | Pipeline PASS | **24** rows (price + arrival), **2** mandis, **3** dates |
| **Live OGD backfill** | CLI + throttle ready | **BLOCKED** — no `OGD_API_KEY`; demo key `Key not authorised` |
| **NASA POWER weather** | Track D PASS | **5,620** rows, **5** TG belt `region_id`s, `2023-05-01` → `2026-05-31` |
| **`overall_quality_score`** | DQS wired (Track E) | **0.1374** (36-mo backfill window, 4 TG expected mandis) |

**Verdict:** Registry and ingest **engineering** are ahead of **corpus** depth. Weather is dense; Agmarknet is proof-scale. Joint signal features remain **blocked**.

---

## 2. Top 3 prioritized gaps

| Rank | Gap ID | Gap | Impact | Unblock |
|------|--------|-----|--------|---------|
| **1** | **OC7-01** | **Live Agmarknet corpus missing (OGD blocked)** — 1099-day window is **99.7% empty**; only fixture slice `2026-06-01`…`2026-06-03` | Market z-scores, Policy spot, DVA mandi series; DQS completeness floor | Register `OGD_API_KEY` → run `agmarknet_backfill.py` (§6); optional OGD catalog zip bulk |
| **2** | **OC7-02** | **Belt market observation vacuum** — **25/27** seeded mandis have **zero** rows; even TG primary is **50%** empty (2/4) | `primary_markets_reporting_pct`, multi-state dispersion, belt-level MI | Live backfill per state (`load_backfill_ogd_states`); OGD 90-day audit; drop/rename weak tuples |
| **3** | **OC7-03** | **Weather–mandi geographic and temporal misalignment** — NASA covers **5 TG districts only**; **22** belt markets have **no** gridded weather; **0** overlapping price days for joins | Weather agent OK alone; **cross-agent** rain×arrival, price×weather correlation | Extend NASA (or IMD) to MH/GJ/AP/KA centroids; align windows; explicit `market_id`↔`region_id` rollup |

**Note:** OC7-01 is the **root ops blocker**; OC7-02 and OC7-03 persist until live load and geography expansion even if the pipeline is green.

---

## 3. Missing markets

### 3.1 Registry vs observations

[MARKET_COVERAGE_REPORT.md](../reviews/MARKET_COVERAGE_REPORT.md) seeded **27** cotton belt mandis with Agmarknet `source_identifiers`. Track B did **not** run backfill.

After [E03_S02](../reviews/E03_S02_COMPLETION_REPORT.md) fixture replay (36-mo window, `--scope telangana` for stats/DQS):

| Scope | Expected | With ≥1 row | Without data | Coverage ratio (latest trade date) |
|-------|----------|-------------|--------------|-----------------------------------|
| **Belt** (`load_expected_market_ids`) | **27** | **2** | **25** | **2/27 ≈ 0.074** |
| **TG primary** (`load_telangana_primary_market_ids`) | **4** | **2** | **2** | **2/4 = 0.50** |

### 3.2 Markets with fixture data (2)

| `market_id` | Distinct dates | Notes |
|-------------|----------------|-------|
| `mkt_tg_khammam_apmc` | 3 | Cotton/kapas in `ogd_telangana_sample.json` |
| `mkt_tg_warangal` | 3 | Same fixture |
| `mkt_tg_karimnagar` | 0 | Sample has Maize, not mapped to cotton mandi |
| `mkt_tg_kesamudram` | 0 | Absent from fixture |

### 3.3 Belt states with zero load (23 markets)

| State | Seeded | With data | Gap |
|-------|--------|-----------|-----|
| Telangana (non-primary 6) | 6 | 0 | Nizamabad, Adilabad, … — no fixture, no live pull |
| Maharashtra | 8 | 0 | Amravati, Yavatmal, … |
| Gujarat | 4 | 0 | Rajkot, Bhavnagar, … |
| Andhra Pradesh | 3 | 0 | Guntur, Adoni, Nandyal |
| Karnataka | 2 | 0 | Raichur, Gulbarga |

**Interpretation:** “**25/27 without Agmarknet data**” is correct for **belt** DQS/stats scope. It is **not** “25 of 27 never seeded” — markets exist in registry; **observations** were never loaded beyond a 3-day TG fixture.

### 3.4 OGD pull vs seed mismatch

Live backfill filters OGD by `load_backfill_ogd_states()` (5 states). Fixture replays **Telangana-only** sample. Until multi-state fixtures or live keys run, **belt expansion (Track B) is registry-only**.

---

## 4. Missing dates (1099-day window)

### 4.1 Target vs actual

| Metric | Track B / E-03-S02 target | Post-fixture @ 5433 |
|--------|---------------------------|---------------------|
| Window | `2023-06-01` → `2026-06-03` | Same |
| Calendar days | **1099** | **1099** |
| Distinct `as_of_date` (price, TG 4-mandi union) | ~1099 (live) | **3** |
| **Completeness ratio** (DQS) | → 1.0 after full load | **3/1099 ≈ 0.0027** |
| Contiguous trading-day series | Required **≥30** days/market for z-scores ([SR-01](./SIGNAL_READINESS_ASSESSMENT.md)) | **None** |
| Arrival season (Oct–Mar) | Full seasons across backfill | **None** in window |

The **1099-day window is mostly empty** by design of current ops: framework and partitions exist; **no live OGD execution**.

### 4.2 Conceptual density

```mermaid
gantt
    title PI7 observation density (conceptual @ 5433)
    dateFormat YYYY-MM-DD
    section NASA POWER (5 TG regions)
    Daily weather rows           :2023-05-01, 2026-05-31
    section Agmarknet target window
    Track A/B 36-mo window       :2023-06-01, 2026-06-03
    section Agmarknet actual
    Fixture 3-day proof          :2026-06-01, 3d
```

### 4.3 Partition readiness

Migration `0010_partition_backfill` supports multi-year price partitions. Empty calendar does **not** block ingest; it **does** block signal math and depresses **36-mo-window** DQS completeness until hundreds of distinct trade days exist.

---

## 5. Missing weather alignment

[NASA_POWER_BACKFILL_REPORT.md](../reviews/NASA_POWER_BACKFILL_REPORT.md): **5,620** rows, **5/5** belt regions — all **Telangana** district centroids (`TELANGANA_COTTON_DISTRICTS`).

### 5.1 Geographic gap

| `region_id` | Weather rows | Mandi markets (seed) | Price rows @ 5433 |
|-------------|--------------|----------------------|-------------------|
| `reg_tg_khammam` | 1,124 | `mkt_tg_khammam_apmc`, `mkt_tg_kesamudram` | >0 (fixture) |
| `reg_tg_warangal` | 1,124 | `mkt_tg_warangal` | >0 |
| `reg_tg_karimnagar` | 1,124 | `mkt_tg_karimnagar` | 0 |
| `reg_tg_nalgonda` | 1,124 | *(no mandi in 27-list)* | — |
| `reg_tg_mahabubabad` | 1,124 | *(no mandi in 27-list)* | — |
| MH / GJ / AP / KA regions | **0** NASA ingest | **17** markets | 0 |

- **22 markets** (all non-TG belt + 5 TG without colocated `region_id` weather) lack gridded daily weather in DB.
- Kesamudram shares Khammam district — weather attribution is **implicit**, not FK-linked ([OBSERVATION_COVERAGE_ANALYSIS.md](./OBSERVATION_COVERAGE_ANALYSIS.md) §6).

### 5.2 Temporal gap

| Series | Start | End |
|--------|-------|-----|
| Weather | `2023-05-01` | `2026-05-31` |
| Agmarknet target | `2023-06-01` | `2026-06-03` |
| Agmarknet actual | `2026-06-01` | `2026-06-03` |

- **One-month skew** at start (May 2023 weather vs June 2023 mandi target).
- **Zero overlapping price days** in the 36-mo window → **no** `as_of_date` joins for joint features (extends PI6 **OC-04**).

### 5.3 DQS weather merge

`record_after_agmarknet_backfill` sets `include_weather=False`. Post-fixture score **0.1374** is **Agmarknet-only**. A merged snapshot (Agmarknet sparse + weather dense) would **overstate** mandi readiness if averaged naïvely — belt signals still need **paired** series.

---

## 6. OGD key blocker

From [E03_S02_COMPLETION_REPORT.md](../reviews/E03_S02_COMPLETION_REPORT.md):

| Check | Status |
|-------|--------|
| `OGD_API_KEY` in `.env` / shell | **Absent** |
| Public demo key probe | **`Key not authorised`** |
| CLI without key | Exits: `OGD_API_KEY required for live backfill (or use --fixture)` |
| Estimated live runtime | ~**1,099** day-queries × (latency + **0.25s** throttle) → **30–90+ min** |

**Ops unblock (ordered):**

1. Register production key at [data.gov.in](https://data.gov.in); add to `.env` (never commit).
2. Run live backfill:

```bash
export DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra
export OGD_API_KEY='<registered-key>'

uv run python scripts/agmarknet_backfill.py \
  --start-date 2023-06-01 \
  --end-date 2026-06-03
```

3. Refresh stats: `agmarknet_backfill.py --stats --write-report --scope belt`.
4. (Optional) OGD catalog **zip bulk** if day-pull is too slow ([AGMARKNET_PRODUCTION_ONBOARDING.md](./AGMARKNET_PRODUCTION_ONBOARDING.md)).

Until step 1–2 complete, **OC7-01** and **OC7-02** cannot close on real data.

---

## 7. Path to `overall_quality_score` > 0.70

### 7.1 How the score is computed

`compute_overall_quality_score` ([`metrics.py`](../../backend/app/services/quality/metrics.py)):

```
score = 0.40 × coverage_ratio
      + 0.35 × completeness_ratio
      + 0.25 × freshness
      − anomaly_penalty   (min 0.3, anomaly_count / row_count)
```

Backfill DQS uses the **full** window length as `window_days` (**1099** for 36-mo), not the default **30-day** rolling window used by daily ingest.

| PI7 fixture inputs | Value |
|--------------------|-------|
| `coverage_ratio` | **2/4 = 0.50** (markets reporting on **latest** `as_of_date` only) |
| `completeness_ratio` | **3/1099 ≈ 0.0027** |
| `freshness` | ~**1.0** if ingest just ran |
| `anomaly_penalty` | Often **material** on fixture rows (non-`VALIDATED` status) → explains **0.1374** despite 50% market coverage |

### 7.2 What “> 0.70” requires (36-mo backfill window)

With **4** TG mandis, **freshness ≈ 1**, **low anomalies**:

| `completeness_ratio` | Approx. distinct days with price data | Illustrative score (cov=1.0) |
|----------------------|--------------------------------------|------------------------------|
| 0.003 (today) | 3 | **~0.14** (observed) |
| 0.15 | ~165 | **~0.70** |
| 0.33 | ~363 | **~0.76** |
| 1.0 | 1099 | **~0.95** |

**Implication:** On a **1099-day** snapshot, **>0.70** needs on the order of **~165+** calendar days with belt/TG price data **and** full market coverage on the latest trade date — not merely “30 days for signals.”

### 7.3 Practical paths (research)

| Path | Actions | Score context |
|------|---------|---------------|
| **A — Live historical load (primary)** | OGD key → full `2023-06-01`…`2026-06-03` backfill → validate rows → reduce anomaly rate | Raises **completeness** toward 0.15+ as reporting days accumulate |
| **B — TG-first DQS scope** | `--scope telangana` (4 mandis) until belt fills; avoid 2/27 coverage denominator | Improves **coverage_ratio** interpretability; does not fix date emptiness alone |
| **C — Daily 30-day DQS (operations)** | After backfill, `record_after_agmarknet_ingest` on rolling window | **4/4** markets × **30/30** days → score **≈ 0.95** (per formula) — better ops gate than 36-mo snapshot |
| **D — Belt weather extension** | NASA (or IMD) for MH/GJ/AP/KA before scoring belt markets | Does not raise Agmarknet score; required for **aligned** belt MI |
| **E — Product/DQS tuning (follow-on)** | Separate “signal window” (30–90d) vs “archive window” (1099d) for backfill snapshots | Prevents punishing historical archive with calendar-day denominator |

**Signal-ready (orthogonal to 0.70):** [E03_S02](../reviews/E03_S02_COMPLETION_REPORT.md) cites **≥30 trading days × 4 TG mandis** before Market z-scores — achievable with weeks of live ingest even if 36-mo DQS completeness remains low.

---

## 8. Full gap registry (prioritized)

| Priority | ID | Gap | Owner track |
|----------|-----|-----|-------------|
| **P0** | OC7-01 | OGD key + live 36-mo backfill | E-03 / Ops |
| **P0** | OC7-02 | 25/27 belt markets empty | E-03 + Track B audit |
| **P0** | OC7-04 | 1099-day completeness ≈ 0 | E-03 (same as OC7-01) |
| **P1** | OC7-03 | Weather geography + zero joint days | Track D + registry FK |
| **P1** | OC7-05 | Fixture-only TG sample; Karimnagar/Kesamudram unmapped | Tests + multi-state fixture |
| **P1** | OC7-06 | Anomaly penalty on proof rows depresses DQS | Validation / ingest status |
| **P2** | OC7-07 | Futures unsigned + MSP absent ([SR-02](./SIGNAL_READINESS_ASSESSMENT.md)) | DS-001 / registry |
| **P2** | OC7-08 | IMD PRIMARY tier (production weather) | WS-01 |

---

## 9. Recommended actions (research only)

| Order | Action | Closes |
|-------|--------|--------|
| 1 | Provision `OGD_API_KEY`; run live `agmarknet_backfill.py` on @ 5433 | OC7-01, OC7-04 |
| 2 | `--stats --write-report --scope belt`; OGD 90-day audit per [MARKET_COVERAGE_REPORT](../reviews/MARKET_COVERAGE_REPORT.md) §6 | OC7-02 |
| 3 | Re-run DQS with `record_after_agmarknet_ingest` (30d) for ops gate; document 36-mo vs 30d semantics | §7 path C |
| 4 | Plan NASA (or IMD) centroids for MH/GJ/AP/KA before belt signal features | OC7-03 |
| 5 | Extend fixtures or zip bulk for CI parity across 27 tuples | OC7-05 |

**Do not** treat **5,620** weather rows alone as belt signal readiness — without mandi price/arrival on the same calendar, MI remains **non-production** ([OBSERVATION_COVERAGE_ANALYSIS](./OBSERVATION_COVERAGE_ANALYSIS.md) §8).

---

## 10. Traceability

| Section | Primary sources |
|---------|-----------------|
| §1–2 State & top gaps | User PI7 payload, E03_S02, this synthesis |
| §3 Markets | [MARKET_COVERAGE_REPORT.md](../reviews/MARKET_COVERAGE_REPORT.md), [E03_S02_COMPLETION_REPORT.md](../reviews/E03_S02_COMPLETION_REPORT.md) |
| §4 Dates | E03_S02, [HISTORICAL_BACKFILL_REPORT.md](../reviews/HISTORICAL_BACKFILL_REPORT.md) |
| §5 Weather | [NASA_POWER_BACKFILL_REPORT.md](../reviews/NASA_POWER_BACKFILL_REPORT.md), [OBSERVATION_COVERAGE_ANALYSIS.md](./OBSERVATION_COVERAGE_ANALYSIS.md) |
| §6 OGD | E03_S02, [AGMARKNET_PRODUCTION_ONBOARDING.md](./AGMARKNET_PRODUCTION_ONBOARDING.md) |
| §7 DQS | [DATA_QUALITY_REPORT.md](../reviews/DATA_QUALITY_REPORT.md), `backend/app/services/quality/metrics.py` |
| §8–9 Signals | [SIGNAL_READINESS_ASSESSMENT.md](./SIGNAL_READINESS_ASSESSMENT.md) |

---

*End of Observation Coverage Gaps — PI7 Track F.*
