# Forecast Readiness Assessment — PI9 Track G

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI9 Track G (KDO — research only; no E-05/E-06 implementation) |
| **Epic gate** | **E-05** Market Intelligence Framework — may engineering begin? |
| **Workspace** | `e9fa355`+ (Tracks A–E complete; `@5433` corpus restored) |
| **Scope** | Signal-layer readiness for MI aggregation and downstream forecast (E-06); Market, Weather, Coverage, Confidence |
| **Out of scope** | E-05 MI runtime, E-06 forecast engine, LangGraph orchestration, Policy/Futures generator implementation |
| **Inputs** | [E04_S01_COMPLETION_REPORT.md](../reviews/E04_S01_COMPLETION_REPORT.md), [E04_S02_COMPLETION_REPORT.md](../reviews/E04_S02_COMPLETION_REPORT.md), [SIGNAL_REPLAY_REPORT.md](../reviews/SIGNAL_REPLAY_REPORT.md), [SIGNAL_QUALITY_REPORT.md](../reviews/SIGNAL_QUALITY_REPORT.md), [SIGNAL_READINESS_RECHECK.md](./SIGNAL_READINESS_RECHECK.md), [FUTURES_SIGNAL_PROTOTYPE.md](./FUTURES_SIGNAL_PROTOTYPE.md), [DS001_FOUNDER_DECISION_PACKAGE.md](./DS001_FOUNDER_DECISION_PACKAGE.md) |

---

## 1. Executive Summary

PI9 closes the **deterministic signal runtime** for cotton Market and Weather agents: generators emit four feature components each, persist via Track C `0012_signal_pi9_contract`, replay **PASS** (5 cycles × Tracks A/B/C), and `SignalQualityService` aggregates coverage, freshness, and confidence without forecast scope.

| Dimension | PI8 (input readiness) | PI9 (runtime + quality) | Verdict |
|-----------|----------------------|-------------------------|---------|
| **Market signals** | PARTIAL — observations ready | **READY** (enhanced degraded) — generator + replay PASS | Real §3.2 transforms on 4/4 TG basket @ 5433 |
| **Weather signals** | PARTIAL — NASA tier-2 @ 5433 | **READY** (non-production label) — generator + replay PASS | 5 TG regions; IMD/belt geography still open |
| **Coverage** | 18/27 mandis; DQS **0.8515** | **0.50** signal agents (2/4); **0.50** required (Market only) | Meets **degraded** threshold; Futures absent |
| **Confidence** | DQS-driven observation quality | Mean **0.615** (Market **0.68**, Weather **0.55**); **fresh** | Adequate for prototype MI; below strict publish bar |

### E-05 verdict

| Question | Answer |
|----------|--------|
| **Can E-05 begin?** | **Yes — enhanced degraded mode** |
| **Recommendation** | **PARTIAL** |
| **Production MI / E-06 strict handoff?** | **NOT READY** — Futures required agent absent; DS-001 founder sign-off still OPEN |

PI9 proves **same-input/same-output** signal determinism and quality telemetry. That is sufficient to **start E-05 engineering** (B/R/N aggregation, regime stubs, partial MI snapshot materialization) with explicit **non-production** guardrails. It is **not** sufficient for production MI publish, licensed DVA gates (G3/G4/G6), or E-06 forecast promotion.

---

## 2. PI9 Signal Runtime Snapshot

Synthesized from Tracks A–E completion reports (@ `2026-06-04`).

| Track | Deliverable | Status |
|-------|-------------|--------|
| **A** | `MarketSignalGenerator` — 4 features, `market-v1.0.0` | **PASS** — 9 unit tests |
| **B** | `WeatherSignalGenerator` — 4 features, `weather_signal_v1.0.0` | **PASS** — 11 unit tests |
| **C** | `SignalSnapshot` @ migration `0012` | **PASS** — append-only + `snapshot_hash` |
| **D** | Replay harness — 5 cycles/track | **PASS** — fixture + `@5433` integration |
| **E** | `SignalQualityService` | **PASS** — 11 tests; sample metrics below |

| Integration DB | Value |
|----------------|-------|
| Corpus | `@5433` restored — 61,544 validated Agmarknet rows; 5,620 NASA weather rows ([SIGNAL_READINESS_RECHECK](./SIGNAL_READINESS_RECHECK.md) §2) |
| Assessment commodity / date | `cotton` / `2026-06-04` |
| Structured signal rows | **2** (Market + Weather) |
| Snapshot aligned | **Yes** — `snapshot_signal_count` = 2 |

---

## 3. Domain Assessments

### 3.1 Market Signals — **READY** (enhanced degraded)

| Criterion | PI8 | PI9 | Status |
|-----------|-----|-----|--------|
| Generator runtime | Not built | **`MarketSignalGenerator` PASS** | **READY** |
| Four §3.2 features | Feasible on observations | Emitted + unit/replay tested | **READY** |
| VALIDATED-only filter | 61,544 validated rows | Enforced in generator | **READY** |
| TG primary basket (4/4) | 4/4 price rows | Basket z-scores on fixture corpus | **READY** |
| Arrival breadth | Single-mandi dense | FG-01 season gate; Khammam-heavy | **PARTIAL** |
| Belt dispersion (18/27 mandis) | 66.7% coverage | Price transforms feasible; not all §3.2 belt features wired | **PARTIAL** |
| Live OGD (SR-01) | BLOCKED | **BLOCKED** — fixture guardrail | **NOT READY** (production) |
| Replay determinism | N/A | **PASS** — 5 cycles, pinned hash | **READY** |

**PI9 delta:** Market moves from *input-feasible* (PI8) to *runtime-proven* with deterministic persistence and replay. Production label remains off until SR-01 live corpus audit.

### 3.2 Weather Signals — **READY** (non-production tier-2)

| Criterion | PI8 | PI9 | Status |
|-----------|-----|-----|--------|
| Generator runtime | Not built | **`WeatherSignalGenerator` PASS** | **READY** |
| Four §4 features | NASA @ 5433 | Emitted + 11 tests | **READY** |
| Validation tier | Rows present; promotion pending | Prefer validated → published → received | **PARTIAL** — Track F batch promotion open |
| 5 TG regions × 36 mo | 5,620 rows | Sufficient for climatology windows | **READY** |
| IMD PRIMARY / belt MH/GJ/AP/KA | NOT READY | NOT READY | **NOT READY** |
| Joint price–weather geography | NOT READY | Price in 18 mandis; weather in 5 TG regions | **NOT READY** |
| Replay determinism | N/A | **PASS** — fixture + `@5433` DB path | **READY** |

Weather is **optional** in cotton `required_agents[]`; its presence improves MI confidence but does not satisfy the Futures gate. Tier-2 NASA path is acceptable for **degraded E-05** with non-production label ([SIGNAL_READINESS_RECHECK](./SIGNAL_READINESS_RECHECK.md) §3.2).

### 3.3 Coverage — **PARTIAL**

From [SIGNAL_QUALITY_REPORT.md](../reviews/SIGNAL_QUALITY_REPORT.md) @ `cotton` / `2026-06-04`:

| Metric | Value | Interpretation |
|--------|-------|----------------|
| Agents present / expected | **2 / 4** | Market, Weather only |
| Required present / expected | **1 / 2** | Market ✓; **Futures ✗** |
| `coverage_ratio` | **0.5000** | Half of registry-weighted agent set |
| `required_coverage_ratio` | **0.5000** | Meets **degraded** floor (Market satisfies minimum) |
| `signals_missing` (required) | **`['Futures']`** | Hard orchestration gap per TDS-009 §9 |
| `optional_agents_missing` | **`['Policy']`** | Regime inputs (`MSP_FLOOR`, `cci_active_procurement`) degraded |
| Observation DQS (@ 5433) | **0.8515** | **> 0.70** target MET ([SIGNAL_READINESS_RECHECK](./SIGNAL_READINESS_RECHECK.md) §4.2) |
| Mandi `coverage_ratio` | **0.6667** (18/27) | Below 0.70 ops target; one mandi short |

**Distinction:** Observation coverage (PI8 DQS) and **signal-agent coverage** (PI9 quality service) measure different layers. PI9 signal coverage at **0.50** is expected for a two-agent PI9 stop rule; it **passes** degraded quality gates but **fails** strict MI publish.

### 3.4 Confidence — **PARTIAL**

| Metric | Value | Target / note |
|--------|-------|---------------|
| Freshness | **`fresh`** | `signal_lag_hours` = 2.0 (< 48h stale threshold) |
| Mean agent confidence | **0.6150** | Market **0.68**; Weather **0.55** |
| Min / max | **0.55 / 0.68** | No agent below degraded floor |
| Futures cap (when built) | **≤ 0.35** | [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §6.5; [FUTURES_SIGNAL_PROTOTYPE](./FUTURES_SIGNAL_PROTOTYPE.md) G-03 |
| Strict MI publish | **Blocked** | Missing Futures + production labels |

Confidence aggregates are **consistent with enhanced degraded mode**: Market leads; Weather penalized by tier-2 source and validation tier. Mean **0.615** supports E-05 **prototype** MI scoring but would trigger **DATA_DEGRADED** or suppressed regimes until Futures + Policy rows exist ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §9).

---

## 4. Cross-Cutting Gates

### 4.1 Required agents (cotton v1.0.0)

```json
"required_agents": ["Market", "Futures"]
```

| Agent | PI9 runtime | E-05 strict gate |
|-------|-------------|------------------|
| **Market** | **Built + PASS** | Contributes real signed \(s_i\) for B/R/N |
| **Futures** | **Absent** — no `FuturesSignalGenerator`; quality lists `signals_missing` | **Hard fail** for production MI publish ([TDS-009](../../docs/tds/) §9; [DS001_FOUNDER_DECISION_PACKAGE](./DS001_FOUNDER_DECISION_PACKAGE.md) §E-04) |
| **Weather** (optional) | **Built + PASS** | MI penalty if omitted — **not** omitted |
| **Policy** (optional) | **Absent** | `MSP_FLOOR`, export-push regimes incomplete |

### 4.2 DS-001 and prototype futures path

| Item | Status | E-05 impact |
|------|--------|-------------|
| Founder sign-off | **OPEN** — Option B unsigned ([DS001_FOUNDER_DECISION_PACKAGE](./DS001_FOUNDER_DECISION_PACKAGE.md)) | Production futures ingest blocked (REQ-071) |
| DS-001 downgrade (Phase-1 → production-only blocker) | **YES** — with guardrails ([FUTURES_SIGNAL_PROTOTYPE](./FUTURES_SIGNAL_PROTOTYPE.md) §7) | Unblocks **parallel** Futures prototype ingest + degraded signal row — **not yet implemented in PI9** |
| NCDEX public bhav prototype | **Recommended** path | Would raise `required_coverage_ratio` to 1.0 in degraded mode when generator ships |

**Interpretation:** DS-001 downgrade **does not** by itself make E-05 **READY**. It removes the *research* blocker for building a degraded Futures row before founder budget executes. PI9 stopped at Market + Weather; E-05 can start **without** Futures code but cannot **publish** strict MI until Futures exists (even degraded).

### 4.3 Replay and determinism (E-05 / E-06 prerequisite)

| Check | Result | Source |
|-------|--------|--------|
| Market 5-cycle replay | **PASS** | [SIGNAL_REPLAY_REPORT](../reviews/SIGNAL_REPLAY_REPORT.md) §3 |
| Weather 5-cycle replay | **PASS** | same |
| Combined `SignalSnapshot` hash stability | **PASS** | same |
| E-01 observation replay chain | Complementary | Unchanged |

Deterministic signal replay is a **necessary** input for E-05 MI replay and E-06 forecast replay (REQ-103). **MET** for Market + Weather scope.

### 4.4 Inherited observation blockers (unchanged)

| ID | Gap | Blocks E-05 how |
|----|-----|-----------------|
| **SR-01** | Live OGD / `OGD_API_KEY` absent | Production MI label; belt audit |
| **SR-02** | DS-001 unsigned | Strict MI; full-weight B/R/N; `CURVE_BACKWARDATION` |
| **SR-03** | MSP / PIB / CCI absent | Policy regimes; `spot_vs_msp_pct` factors |
| **OC7-03** | Weather geography (5 TG vs 18 mandis) | Belt-level MI factors; cross-state dispersion |
| **OC7-02** | 9/27 fixture-empty mandis | Mandi `coverage_ratio` < 0.70 |

---

## 5. E-05 Readiness Decision

### 5.1 Can E-05 begin?

| Path | Verdict | Rationale |
|------|---------|-----------|
| **E-05 engineering start (degraded MI)** | **ALLOWED** | Market + Weather generators, snapshot persistence, replay PASS, quality service PASS; TDS-009 §4.1 allows optional-agent gaps with penalties |
| **E-05 production MI publish (F-05-05)** | **BLOCKED** | Futures required agent missing; TDS-009 §9 fail-closed |
| **E-06 forecast engine start** | **BLOCKED** | E-06 depends on E-05; strict handoff requires full required-agent snapshot ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §8 step 5–6) |
| **Spot-only forecast research (Track D)** | **Already allowed** | [FORECAST_RESEARCH_DESIGN.md](./FORECAST_RESEARCH_DESIGN.md) — lower confidence; cannot pass G6 |

### 5.2 Recommendation matrix

| Gate | PI8 | PI9 |
|------|-----|-----|
| Market signal runtime | Not built | **READY** (degraded) |
| Weather signal runtime | Not built | **READY** (tier-2) |
| Signal coverage (agents) | N/A | **PARTIAL** (0.50) |
| Confidence for MI | DQS only | **PARTIAL** (0.615 mean) |
| **E-05 begin** | BLOCKED (no E-04 runtime) | **PARTIAL — begin degraded** |
| **Production MI / E-06** | BLOCKED | **NOT READY** |

### 5.3 Top blockers (ordered)

| Rank | Blocker | Evidence | Blocks |
|------|---------|----------|--------|
| **1** | **Futures agent not runtime-built** | `signals_missing: ['Futures']`; PI9 stop at M+W; DS-001 OPEN | Strict MI publish; full B/R/N weights (Futures **0.25**); `CURVE_BACKWARDATION`; E-06 G6 |
| **2** | **DS-001 founder sign-off OPEN** | [DS001_FOUNDER_DECISION_PACKAGE](./DS001_FOUNDER_DECISION_PACKAGE.md) — Option B unsigned | Production futures ingest; licensed hold-to-curve (FD-003); production promotion |
| **3** | **SR-01 live OGD / fixture guardrail** | 18/27 fixture corpus; no `OGD_API_KEY` | Production MI label; unaudited belt tuples |
| **4** | **Policy agent + MSP inputs absent** | Optional agent missing; `msp_inr_quintal` stub | `MSP_FLOOR` regime; Policy-weighted factors (**0.15**) |
| **5** | **Weather belt geography (OC7-03)** | NASA 5 TG only vs 18 price mandis | Belt joint features; full weather MI confidence |

Prototype futures path ([FUTURES_SIGNAL_PROTOTYPE](./FUTURES_SIGNAL_PROTOTYPE.md)) addresses **#1–#2 for engineering only** once `FuturesSignalGenerator` + NCDEX public bhav ingest are built — it does **not** close production gates.

---

## 6. Recommended PI9 → E-05 Follow-on

| # | Action | Closes |
|---|--------|--------|
| **1** | **START E-05 (enhanced degraded)** — B/R/N on Market + Weather signed contributions; explicit `DATA_DEGRADED` / non-production labels | MI framework wiring, AC harness |
| **2** | Implement **FuturesSignalGenerator** on NCDEX public bhav prototype (guardrails G-01–G-10) | `required_coverage_ratio` → 1.0 degraded; regime `CURVE_BACKWARDATION` dev logs |
| **3** | Founder **DS-001 Option B** + contract on file | Production futures; REQ-071; strict MI path |
| **4** | Promote weather rows to **validated** (Track F); register **OGD_API_KEY** + live belt audit | Confidence uplift; SR-01 |
| **5** | Policy stub + `msp_inr_quintal` seed | SR-03; `MSP_FLOOR` regime |

---

## 7. Return Payload (Track G)

| Field | Value |
|-------|-------|
| **Report path** | `docs/research/FORECAST_READINESS_ASSESSMENT.md` |
| **E-05 verdict** | **PARTIAL** — **begin enhanced degraded**; production MI / E-06 strict handoff **NOT READY** |
| **Market signals** | **READY** (degraded) |
| **Weather signals** | **READY** (tier-2, non-production) |
| **Coverage** | **PARTIAL** — 0.50 agent coverage; observation DQS **0.8515** MET |
| **Confidence** | **PARTIAL** — mean **0.615**, fresh |
| **Top blockers** | **(1) Futures agent absent** · **(2) DS-001 OPEN** · **(3) SR-01 live OGD / fixture guardrail** |

---

## 8. Traceability

| Section | Sources |
|---------|---------|
| §1–2 PI9 runtime | E04_S01/S02, SIGNAL_REPLAY, SIGNAL_QUALITY reports |
| §3 Domains | SIGNAL_ENGINE_V1 §3–§4, SIGNAL_READINESS_RECHECK §3 |
| §4 Gates | cotton.json, DS001_FOUNDER_DECISION_PACKAGE, FUTURES_SIGNAL_PROTOTYPE §7 |
| §5–7 Verdict | TDS-014 E-05/E-06 deps, SIGNAL_ENGINE_V1 §8–§9, FORECAST_RESEARCH_DESIGN |

---

*End of Forecast Readiness Assessment — PI9 Track G.*
