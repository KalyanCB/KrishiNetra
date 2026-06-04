# Signal Readiness Recheck — PI8 Track F

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI8 Track F (KDO — research only; no signal runtime) |
| **Epic** | E-04 Domain Agents — **input readiness recheck** (post PI8 Tracks A, C, E) |
| **Workspace** | `058230e` + uncommitted |
| **DB** | `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra` |
| **Scope** | Market and Weather signal readiness; E-04 viability; strict MI blockers |
| **Out of scope** | Signal runtime, LangGraph orchestration, Policy deep-dive, dashboard UI |
| **Baseline** | [SIGNAL_READINESS_GATE.md](./SIGNAL_READINESS_GATE.md) (PI7 Track G) |
| **PI8 inputs** | [OBSERVATION_VALIDATION_REPORT.md](../reviews/OBSERVATION_VALIDATION_REPORT.md), [MARKET_COVERAGE_IMPROVEMENT.md](../reviews/MARKET_COVERAGE_IMPROVEMENT.md), [WEATHER_ACTIVATION_REPORT.md](../reviews/WEATHER_ACTIVATION_REPORT.md), [DS001_FOUNDER_DECISION_PACKAGE.md](./DS001_FOUNDER_DECISION_PACKAGE.md) |

---

## 1. Executive Summary

PI8 closes three PI7 observation blockers on the integration DB: **belt fixture coverage** (Track E), **row validation / anomaly penalty removal** (Track A), and **weather persistence activation** (Track C). Corpus state @ 5433:

| Metric | PI7 @ 5433 | PI8 @ 5433 | Δ |
|--------|------------|------------|---|
| Markets reporting (latest date) | **2 / 27** | **18 / 27** | +16 mandis |
| TG primary basket (`load_telangana_primary_market_ids`) | **2 / 4** | **4 / 4** | Karimnagar, Kesamudram populated |
| Price / arrival rows (36-mo window) | 8,792 | **61,544** | +52,752 price; arrivals validated |
| Row validation | 0 validated | **61,544 validated** | 0 rejected |
| `overall_quality_score` | **0.3161** | **0.8515** | **+0.5354** |
| `coverage_ratio` | 0.074 | **0.6667** | +0.5926 |
| `anomaly_penalty` | 0.30 (max) | **0.00** | Track A |
| `weather_observation` (NASA) | 0 @ 5433 | **5,620** | Track C |

| Question | Recheck answer |
|----------|----------------|
| **Market signal readiness** | **PARTIAL** — TG §3.2 price basket **READY**; belt dispersion improved; **fixture not live OGD**; arrivals still single-mandi dense |
| **Weather signal readiness** | **PARTIAL** — tier-2 NASA **READY** (5 TG regions); IMD + multi-state belt weather **NOT READY** |
| **DQS > 0.70 @ 36-mo belt snapshot** | **MET** — **0.8515** (was NOT MET @ 0.3161) |
| **E-04 viable?** | **Yes — enhanced degraded mode** — real Market price transforms + Weather tier-2 feasible; agent wiring + AC harness |
| **E-04 strict / production MI?** | **No — still BLOCKED** — `required_agents: ["Market","Futures"]`; **DS-001 OPEN** |

---

## 2. PI8 Integration Snapshot (@ 5433)

Synthesized from PI8 Track A, C, E reports and user payload.

| Check | Result |
|-------|--------|
| Cotton belt markets seeded | **27** |
| Markets with price rows (36-mo) | **18 / 27** |
| TG primary with price rows | **4 / 4** — `mkt_tg_khammam_apmc`, `mkt_tg_warangal`, `mkt_tg_karimnagar`, `mkt_tg_kesamudram` |
| Backfill window | `2023-06-01` → `2026-06-03` (**1,099** days) |
| Observation rows validated | **61,544** (60,445 price + 1,099 arrival) |
| `weather_observation` (`nasa_power`) | **5,620** — `2023-05-01` → `2026-05-31`; 5 TG `region_id`s |
| `data_quality_snapshot` (post validation refresh) | `overall_quality_score` **0.8515**; `coverage_ratio` **0.6667**; `completeness_ratio` **1.0**; `anomaly_count` **0** |
| `OGD_API_KEY` | **Absent** — live backfill **BLOCKED** (SR-01 unchanged) |
| DS-001 founder sign-off | **OPEN** — no NDU/vendor contract on file |
| Signal runtime (`structured_signal`) | **Not built** — ingest + research only |

**Interpretation:** Fixture replay (`ogd_cotton_belt_sample.json`) now spans **5 states** and **18 mandis**, not just 2 Telangana markets. Validation promoted all pending rows and removed the **0.30** anomaly ceiling. Weather tier is live on the same DB instance PI7 DQS trend flagged as empty.

---

## 3. Domain Readiness Verdicts

| Domain | PI7 | PI8 | One-line rationale |
|--------|-----|-----|-------------------|
| **Market** | PARTIAL | **PARTIAL** (↑) | Price depth + 4/4 TG basket + DQS **READY** for transforms; fixture corpus + sparse arrivals + SR-01 keep production label off |
| **Weather** | PARTIAL | **PARTIAL** (↑) | NASA tier-2 **READY** @ 5433; IMD + MH/GJ/AP/KA gridded + joint mandi joins still open |
| **Policy** | PARTIAL | **PARTIAL** (—) | Out of Track F scope; MSP / PIB / CCI unchanged ([SIGNAL_READINESS_GATE](./SIGNAL_READINESS_GATE.md) §3.3) |

### 3.1 Market — **PARTIAL** (↑ from PI7)

| Capability | PI7 | PI8 | Status |
|------------|-----|-----|--------|
| Production OGD pipeline + belt backfill CLI | READY (code) | READY (code) | Unchanged |
| 36-mo calendar density (reporting mandis) | 2 mandis × 1,099d | **18 mandis** × 1,099d | **READY** |
| 4-mandi TG primary basket | 2/4 | **4/4** | **READY** (price) |
| `price_trend_zscore` (§3.2, ≥30d × 4) | BLOCKED | **Feasible** — 1,099d × 4 mandis validated | **READY** (fixture) |
| `arrival_zscore` (§3.2, Oct–Mar) | BLOCKED | **1,099** arrival rows; **single-mandi** density (Khammam); no 4-mandi arrival series | **PARTIAL** |
| `regional_strength_index` (belt dispersion) | BLOCKED (2 mandis) | **18** cross-state mandis | **PARTIAL** → approaching READY |
| Belt `primary_markets_reporting_pct` | 2/27 (7.4%) | **18/27 (66.7%)** | **PARTIAL** — below ~70% live target; DQS term met |
| Row validation / anomaly | 8,792 non-validated | **0** anomalies | **READY** |
| DQS confidence inputs | PARTIAL | **0.8515** overall | **READY** (fixture) |
| Live OGD corpus (SR-01) | BLOCKED | **BLOCKED** | **NOT READY** (production) |
| Futures basis fallback | BLOCKED (DS-001) | BLOCKED | **NOT READY** |

**PI8 delta vs PI7 gate Top-3 #2:** Validation pipeline **closed OC7-06** — anomaly penalty **0.30 → 0.00**, DQS **0.5515 → 0.8515** at 18/27 coverage.

**PI8 delta vs PI7 gate Top-3 #3:** **4/4 TG primary** populated — §3.2 price z-score path **unblocked** for degraded E-04 (no longer wiring-only neutral stubs for price trend).

**Remaining Market gaps:** (1) **9/27** fixture-empty mandis; (2) **SR-01** live OGD for production promotion; (3) **arrival** breadth across basket; (4) **DS-001** basis fallback.

### 3.2 Weather — **PARTIAL** (↑ from PI7)

| Capability | PI7 | PI8 | Status |
|------------|-----|-----|--------|
| `weather_observation` store + NASA backfill | READY (code); **0 rows @ 5433** | **5,620 rows @ 5433** | **READY** |
| Weather agent AC-05 `source_refs[]` (tier-2) | READY (corpus elsewhere) | **READY** — 36-mo × 5 TG districts | **READY** |
| ≥24 months per belt region | N/A @ 5433 | **758** rows / 24-mo window × 5 regions | **READY** |
| Rainfall + temperature validated | — | **0** nulls / **0** out-of-range | **READY** |
| IMD PRIMARY anomalies / categories | NOT READY | NOT READY | **NOT READY** (WS-01) |
| Belt MH/GJ/AP/KA gridded weather | NOT READY | NOT READY — **22** non-TG belt mandis lack NASA rows | **NOT READY** |
| Joint price–weather features | NOT READY | NOT READY — no explicit market↔region FK; price in 18 mandis, weather in 5 TG regions | **NOT READY** |
| DQS weather tier merge | missing @ 5433 | **Activatable** — ingest triggers `record_after_weather_ingest` | **PARTIAL** — blend not re-scored in Track A refresh |

**PI8 delta vs PI7:** Track C **closed SI-02 on integration DB** — weather tier no longer empty on @ 5433 ([WEATHER_ACTIVATION_REPORT](../reviews/WEATHER_ACTIVATION_REPORT.md) §1).

**Weather agent is optional** in cotton registry — omission penalizes MI confidence but does not abort pipeline. Tier-2 NASA path is sufficient for **degraded E-04 Weather agent** with non-production label.

---

## 4. Cross-Cutting Gates

### 4.1 Required agents (orchestration)

From [`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json):

```json
"required_agents": ["Market", "Futures"]
```

| Agent | PI8 input readiness | E-04 strict gate |
|-------|---------------------|------------------|
| **Market** | **PARTIAL** (↑) — real §3.2 price transforms feasible | Degraded **enhanced** signal possible; **not** full production MI without live OGD label |
| **Futures** | **BLOCKED** (DS-001) | **Hard fail** — no strict MI publish ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §8) |

### 4.2 Data quality (@ 5433)

| Metric | PI7 | PI8 | Target |
|--------|-----|-----|--------|
| `overall_quality_score` | 0.3161 | **0.8515** | **> 0.70** |
| `coverage_ratio` | 0.074 (2/27) | **0.6667** (18/27) | ≥ 0.70 (~19+ mandis) |
| `completeness_ratio` | 1.0 | **1.0** | Maintained |
| `anomaly_penalty` | ~0.30 | **0.00** | Near 0 |

Formula ([`metrics.py`](../../backend/app/services/quality/metrics.py)):

```
score = 0.40 × coverage_ratio + 0.35 × completeness_ratio + 0.25 × freshness − anomaly_penalty
```

**PI8 decomposition (Agmarknet-only refresh @ validation):**

| Component | Approx. contribution |
|-----------|-------------------|
| Coverage | 0.4 × 0.6667 ≈ **0.267** |
| Completeness | 0.35 × 1.0 = **0.350** |
| Freshness | 0.25 × ~0.95 ≈ **0.235** |
| Anomaly penalty | **0.000** |
| **Total** | **≈ 0.852** (matches **0.8515**) |

**DQS > 0.70:** **MET** — driven by validation (penalty removal) + 18/27 coverage. **Coverage_ratio alone** (0.6667) still below the **0.70** market-breadth ops target (~19/27 mandis); one additional reporting mandi would cross that line.

### 4.3 Gap IDs (PI7 → PI8)

| ID | Gap | PI7 | PI8 |
|----|-----|-----|-----|
| **SR-01** / **OC7-01** | Live 36-mo Agmarknet (OGD key) | OPEN | **OPEN** |
| **OC7-02** | Belt mandis empty | OPEN (25/27) | **PARTIAL** (9/27 empty) |
| **OC7-03** | Weather geography + joint alignment | OPEN | **OPEN** |
| **OC7-06** | Row validation / anomaly penalty | OPEN | **CLOSED** (Track A) |
| **SR-02** | DS-001 Futures unsigned | OPEN | **OPEN** |
| **SR-03** | MSP + PIB/CCI policy ingest | OPEN | **OPEN** |
| **SI-02** | Weather persistence @ 5433 | CLOSED (code) / empty DB | **CLOSED** (Track C) |
| **SI-04** | DQS writer | CLOSED | **CLOSED** — score now reflects depth |

---

## 5. E-04 Viability

### 5.1 Is E-04 now viable?

| Path | PI7 | PI8 | Verdict |
|------|-----|-----|---------|
| Agent implementation + unit transforms | Yes (degraded) | **Yes — enhanced** | Market price §3.2 + Weather tier-2 on real observations |
| Degraded Market/Policy stubs | Yes (neutral wiring) | **Partially superseded** — Market can emit **non-neutral** price-trend signals on 4/4 TG basket |
| Weather agent (tier-2 NASA) | Yes (non-production) | **Yes** — 5,620 rows @ 5433; label non-production |
| Futures agent (required) | Stub only | **Stub only** | **BLOCKED** until DS-001 |
| Strict `SignalSnapshot` → Forecast | No | **No** | **BLOCKED** |
| E-04 runtime (code) | Not built | Not built | Engineering follow-on, not a data gate |

**E-04 verdict:** **VIABLE for enhanced degraded start** — PI8 observation depth exceeds PI7 wiring-only threshold. Proceed with agent transforms, AC-01/AC-06 harness, and explicit **non-production** fixture guardrail until SR-01 + DS-001 close.

**Not viable for:** production MI promotion, hold-to-curve DVA (FD-003), or strict orchestration publish.

### 5.2 What still blocks strict MI?

Ordered by severity:

| Rank | Blocker | Evidence | Blocks |
|------|---------|----------|--------|
| **1** | **DS-001 unsigned (SR-02)** | [DS001_FOUNDER_DECISION_PACKAGE](./DS001_FOUNDER_DECISION_PACKAGE.md) — founder sign-off blank; no NDU/vendor contract | **Strict E-04** — Futures in `required_agents[]`; `curve_*`, `basis_*`, hold-to-curve undefined |
| **2** | **E-04–E-07 runtime not built** | PI7/PI8 program status — signal engine design-only | No `SignalSnapshot` generation regardless of observation depth |
| **3** | **Live OGD corpus (SR-01)** | `OGD_API_KEY` absent; 18/27 from **fixture** replay | Production promotion; belt tuples un audited against live OGD; 9 mandis still empty |
| **4** | **Policy inputs (SR-03)** | `msp_inr_quintal` absent; no PIB/CCI ingest | Policy production tiers; `spot_vs_msp_pct`; MSP_FLOOR regime |
| **5** | **Weather belt geography (OC7-03)** | NASA rows for **5 TG regions only**; 18 price mandis span MH/GJ/AP/KA | Belt-level weather–price joint features; full MI confidence on cross-state dispersion |
| **6** | **Arrival basket depth** | 1,099 arrivals validated; single-mandi concentration | Full §3.2 `arrival_zscore` across 4-mandi basket Oct–Mar |
| **7** | **Coverage tail (9/27 mandis)** | Fixture-empty list in [MARKET_COVERAGE_IMPROVEMENT](../reviews/MARKET_COVERAGE_IMPROVEMENT.md) §4.1 | `coverage_ratio` < 0.70; belt-representative Policy spot |

**DS-001 remains the hard orchestration gate** per founder memo:

> **Without B:** Market/Weather/Policy agents runnable on observations; Futures emits **degraded** signal only; **strict MI / production promotion blocked** per TDS-009.

PI8 does **not** change DS-001 status.

---

## 6. PI7 → PI8 Decision Matrix

| Gate | PI7 | PI8 |
|------|-----|-----|
| **Market** | PARTIAL | **PARTIAL** (↑) |
| **Weather** | PARTIAL | **PARTIAL** (↑) |
| **Signal-ready (production)** | NOT READY | **NOT READY** |
| **E-04 start (degraded)** | ALLOWED | **ALLOWED — enhanced** |
| **E-04 strict / MI publish** | BLOCKED | **BLOCKED** |
| **DQS > 0.70 @ 36-mo belt snapshot** | NOT MET (0.3161) | **MET (0.8515)** |

### Recommended PI8 follow-on (ordered)

| # | Action | Closes |
|---|--------|--------|
| **1** | **START E-04 (enhanced degraded)** — Market price + Weather tier-2 transforms on @ 5433 corpus | Agent wiring, AC harness |
| **2** | Founder **DS-001 OPTION B** + futures ingest path | SR-02, strict orchestration |
| **3** | Register `OGD_API_KEY`; live belt backfill + 90-day audit | SR-01, OC7-02 tail, production label |
| **4** | Arrival channel across TG basket (G6) | Full §3.2 `arrival_zscore` |
| **5** | `msp_inr_quintal` + PIB/CCI design | SR-03 |
| **6** | NASA (or IMD) for non-TG belt regions before belt MI | OC7-03 |

---

## 7. Return Payload (Track F)

| Field | Value |
|-------|-------|
| **Report path** | `docs/research/SIGNAL_READINESS_RECHECK.md` |
| **Market verdict** | **PARTIAL** (↑) |
| **Weather verdict** | **PARTIAL** (↑) |
| **E-04 viable?** | **Yes — enhanced degraded mode** (not strict MI) |
| **Strict MI blockers (top 3)** | **(1) DS-001 / Futures unsigned** · **(2) E-04 runtime not built** · **(3) SR-01 live OGD + fixture guardrail** |
| **DQS > 0.70** | **MET** @ **0.8515** |

---

## 8. Traceability

| Section | Sources |
|---------|---------|
| §1–2 PI8 state | User PI8 payload, OBSERVATION_VALIDATION_REPORT, MARKET_COVERAGE_IMPROVEMENT, WEATHER_ACTIVATION_REPORT |
| §3 Domains | SIGNAL_READINESS_GATE (PI7), SIGNAL_ENGINE_V1 §3–§5, expected_markets.py |
| §4–5 DQS / E-04 | OBSERVATION_VALIDATION_REPORT §4, metrics.py, DS001_FOUNDER_DECISION_PACKAGE |
| §6–7 Verdict | This synthesis |

---

*End of Signal Readiness Recheck — PI8 Track F.*
