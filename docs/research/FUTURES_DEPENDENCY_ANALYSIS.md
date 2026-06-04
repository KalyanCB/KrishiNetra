# Futures Dependency Analysis — DVA Without Licensed Feed

**Date:** 2026-06-04  
**PI:** PI2 Track G (KDO rerun — Agent 4)  
**Input:** [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md), TDS-007 §3–§9, TDS-008 §10, TDS-009 §4.1, TDS-004 §4.5, founder FD-003, FD-030, REQ-071, REQ-082, DD-005  
**Status:** FOUNDER DECISION REQUIRED on DS-001 — analysis only, no new requirements

---

## 1. Question

Can **Decision Value Added (DVA)** be proven without a licensed commercial futures feed (REQ-071, DD-005)?

---

## 2. Executive Answer

| Capability | Without licensed futures? |
|------------|-------------------------|
| **Schema / persistence** | **Yes** — E-01 complete; `futures_feed_ok` on DataQualitySnapshot |
| **Market-only MI (spot mandi)** | **Partial** — Agmarknet sufficient for price/arrival intelligence |
| **Full TDS-007 feature vector** | **No** — `basis_*`, `curve_*`, `open_interest_change`, `carry_implied_*` require licensed feed |
| **TDS-007 gate G6** (Futures + Market ≥ 99% days) | **No** |
| **REQ-082 / FD-003 hold-to-curve benchmark** | **No** |
| **REQ-133 / FD-030 basis modeling** | **Partial** — spot-only fallback degrades confidence; full basis needs concurrent licensed futures + mandi |
| **TDS-009 required_agents publish** | **No** — cotton registry requires `[Market, Futures]`; missing Futures → publish blocked or degraded |
| **Credible DVA bake-off (E-06)** | **Partial** — spot + weather + policy exploratory track only; **not production-grade** per DD-005 and FD-003 |

**Verdict:** DVA can be **explored** on spot-only features for engineering and research progress, but **cannot be proven production-ready** without NDU/vendor contract. Public NCDEX bhav download is dev-only, not REQ-071 compliant.

---

## 3. Why Futures Are Foundational (Baseline)

| Founder / REQ | Implication |
|---------------|-------------|
| FD-003 | System must **outperform hold-to-futures-curve** before claiming value |
| FD-030 | Basis modeling + futures feed mitigate Agmarknet lag/gaps |
| REQ-071 | Commercial futures feeds required for production ingest |
| REQ-082 | Hold-to-curve is explicit backtest benchmark (TDS-008 §10.2) |
| REQ-133 | Basis vs Agmarknet needs concurrent licensed futures + mandi spot |
| DC-005 | Cotton signal set includes futures curve |
| DA-002 | Commercial futures obtainable and materially improve intelligence |

Hold-to-curve baseline (TDS-008 §10.2):

\[
V_{curve} = (p_{futures,h} - p_0) \cdot q - Carry_{curve}(h)
\]

Without licensed \(p_{futures,h}\), the primary economic benchmark is undefined — DVA vs curve cannot be computed credibly.

---

## 4. Dependency Classification

### 4.1 Ingestion / observations

| Component | Classification | Notes |
|-----------|----------------|-------|
| Agmarknet price/arrival ingest | **REQUIRED** | Primary spot; no futures dependency |
| IMD / weather ingest | **REQUIRED** (for full signal set) | Independent of futures |
| Policy / PIB ingest | **REQUIRED** (for MSP/CCI path) | Independent of futures |
| `FuturesObservation` from licensed feed | **REQUIRED** (production) | Blocked until DS-001 closes |
| Public NCDEX bhav scrape | **DEFERRED** (prod) | Dev-only with legal waiver per DS-001 §4.5 |
| NCDEX direct NDU EOD | **OPTIONAL** (fallback path) | ~₹15k/yr; satisfies REQ-071 when executed |
| NCDEX authorized vendor EOD API | **REQUIRED** (primary path) | DS-001 recommendation; ₹3–8L Y1 planning |

### 4.2 Signal stack

| Component | Classification | Notes |
|-----------|----------------|-------|
| Market Agent | **REQUIRED** | Agmarknet primary; basis fallback needs Futures when licensed |
| Futures Agent | **REQUIRED** (cotton registry) | TDS-009 `required_agents: [Market, Futures]` |
| Weather Agent | **OPTIONAL** | Confidence penalty if missing |
| Policy Agent | **OPTIONAL** | Confidence penalty; MSP/CCI rule still works from registry + spot |
| Demand / Global | **OPTIONAL** | Confidence penalty |
| 6-agent SignalSnapshot | **REQUIRED** for full replay | Missing Futures → partial snapshot or explicit failed agent row |
| Degraded Futures signal (`futures_feed_ok=false`) | **OPTIONAL** (interim) | Emit with confidence penalty; does not satisfy G6 or REQ-071 |

### 4.3 Feature / forecast stack

| Component | Classification | Notes |
|-----------|----------------|-------|
| `forecast_version` schema | **REQUIRED** (done E-01-S06) | Stores horizons regardless of data |
| Market features (`spot_*`, `arrival_*`) | **REQUIRED** | Spot-only path viable |
| Weather / Policy features | **REQUIRED** (for full DC-005 set) | Independent |
| Futures features (`curve_slope`, `curve_level_near`, `open_interest_change`, `basis_futures_spot`, `carry_implied_30/60/90`) | **REQUIRED** (full TDS-007 §5.2) | Blocked DS-001 |
| Spot-only forecast candidate | **OPTIONAL** (research) | FORECAST_RESEARCH_DESIGN allows reduced feature set — lower confidence, cannot pass G6 |
| Forecast gate G6 | **DEFERRED** until licensed feed | Futures + Market ≥ 99% days |
| Forecast gate G3/G4 (DVA promotion) | **DEFERRED** without curve baseline | Cannot claim value vs FD-003 benchmark |

### 4.4 MI / intelligence stack

| Component | Classification | Notes |
|-----------|----------------|-------|
| Bullish/bearish/neutral scores | **REQUIRED** (schema) | Futures weight 0.25 — missing → reweight or abort |
| `CURVE_BACKWARDATION` regime | **DEFERRED** without futures | TDS-009 §5.1 |
| `DATA_DEGRADED` on missing optional agents | **OPTIONAL** path | Weather/Policy missing |
| MI publish when Futures missing | **BLOCKED** (strict) or **DEGRADED** (if founder allows interim) | TDS-009 §9: required missing → no MI_SNAPSHOT_READY |
| `futures_feed_ok` flag | **REQUIRED** | E-01-S08; drives confidence penalties |

### 4.5 Decision stack

| Component | Classification | Notes |
|-----------|----------------|-------|
| NHV core (forecast − spot − carry costs) | **REQUIRED** | Spot \(p_0\) from MI; no futures needed for formula |
| MSP proximity (±3%) | **REQUIRED** | Spot vs registry MSP — no futures |
| MSP/CCI floor rule | **REQUIRED** | Policy signal + spot |
| Hold vs sell using futures curve | **DEFERRED** | REQ-082, FD-003 |
| Basis-aware partial sell | **DEFERRED** | FD-030 full basis |
| Farmer/trader core sell/hold (spot forecast) | **OPTIONAL** spot-only | Reduced DVA claim; exploratory only |
| DVA aggregation vs curve | **DEFERRED** | \(DVA = \overline{V_{KN}} - \max(\overline{V_{sell}}, \overline{V_{curve}})\) needs \(V_{curve}\) |

### 4.6 Evaluation / promotion

| Gate / metric | Classification | Without futures |
|---------------|----------------|-----------------|
| G1 Leakage audit | **REQUIRED** | Passable |
| G2 Replay hash | **REQUIRED** | Passable on spot-only snapshot |
| G3 DVA > 3% | **DEFERRED** | Cannot vs curve baseline |
| G4 Positive DVA > 70% months | **DEFERRED** | Same |
| G5 Forecast success ≥ 97% | **OPTIONAL** partial | Spot-only runs possible |
| G6 Futures + Market ≥ 99% | **DEFERRED** | Fail until DS-001 |
| G7 No LLM audit | **REQUIRED** | Independent |
| Three-strategy backtest (FD-020) | **DEFERRED** (full) | Sell-only + KN exploratory; curve leg missing |

---

## 5. What Works Without Licensed Futures

| Path | Components | DVA evidence quality |
|------|------------|---------------------|
| **A — Spot minimal** | Agmarknet 24 mo + registry MSP | **Low** — seasonal patterns only; no curve benchmark |
| **B — Spot + weather + policy** | Path A + IMD 36 mo + PIB/CCI | **Medium** — procurement floors, harvest rain; still no FD-003 bar |
| **C — Path B + Global/USDA** | + WASDE, ICAC | **Medium+** — export/inventory context |
| **D — Licensed NCDEX KAPAS EOD** | Path B/C + DS-001 primary/fallback | **High** — meets DD-005, G6, basis features, hold-to-curve |

**Engineering value of A–C:** Unblock E-03 ingest design, agent math validation, spot-only forecast research (FORECAST_RESEARCH_DESIGN).  
**Product value claim:** Requires Path D before production promotion.

---

## 6. Interim Behaviors (Pre–DS-001)

Per TDS-004 §4.5 and TDS-007 §11:

| Condition | System behavior |
|-----------|-----------------|
| `futures_feed_ok=false` | Futures Agent emits degraded signal; confidence penalty; thin OI additional penalty (DS-001 §3) |
| Missing Futures in required_agents | MI publish **blocked** (TDS-009 §9) OR ops override with DATA_DEGRADED (founder ack pending) |
| Agmarknet gap + no futures | Market agent confidence ↓; no basis-implied spot fallback (FD-030 partial) |
| Dev public bhav | Parser validation only; **not** REQ-071; explicit legal waiver |

---

## 7. DS-001 Status (Unchanged)

| Field | Value |
|-------|-------|
| Primary path | NCDEX KAPAS EOD via authorized domestic vendor (Accelpix, Accord, GDF shortlist) |
| Fallback | Direct NCDEX NDU EOD Bhav (~₹15k/yr domestic) |
| Deferred Phase 1 | Bloomberg/Refinitiv, MCX dual-exchange, real-time L1 |
| Founder approval | **Not recorded in repo** — status FOUNDER DECISION REQUIRED |
| Year 1 budget (planning) | ₹3–8 lakhs all-in (vendor + exchange + legal) |
| Blocks when closed | E-03 production futures ingest, E-06 hold-to-curve bake-off |

---

## 8. Phase 1 Sequencing Recommendation

1. **Continue E-01** — schema unblocked (`futures_feed_ok`, forecast horizons)
2. **Parallel DS-001** — RFP + NDU quote; do not block E-01 S07/S11 on contract
3. **E-03 ingest** — Agmarknet + weather + policy first; futures ingest slot ready with quality flags
4. **E-05 agents** — Implement Market/Weather/Policy math (SIGNAL_MATH_SPECIFICATION); stub Futures Agent with degraded mode
5. **E-06 bake-off** — **Dual track:** (A) spot-only exploratory for pipeline validation; (B) licensed track when DS-001 closes for promotion gates G3/G4/G6

---

## 9. Risks if Futures Deferred Indefinitely

| Risk | Severity | Mitigation |
|------|----------|------------|
| Cannot satisfy REQ-071 / DD-005 | **High** — production blocker | Execute DS-001 primary or fallback NDU |
| Cannot satisfy FD-003 value proposition | **High** — no curve benchmark | Hold product claims until Path D |
| Thin KAPAS OI even when licensed | Medium | `futures_feed_ok` + confidence penalties (TDS-006/TDS-011) |
| Market agent over-weight in MI | Medium | Temporary registry weight adjustment only with founder ack |
| Agmarknet gaps without basis | Medium | FD-030 mitigation incomplete without futures |
| False promotion on spot-only DVA | **High** | Gate G6 + FD-003 explicitly block |

---

## 10. Summary Table — REQUIRED / OPTIONAL / DEFERRED

| Layer | REQUIRED (production) | OPTIONAL (interim/research) | DEFERRED |
|-------|----------------------|----------------------------|----------|
| **Data** | Licensed NCDEX KAPAS EOD + Agmarknet + IMD | Public bhav dev parse | Real-time L1, MCX dual, Bloomberg |
| **Agents** | Market + Futures | Weather, Policy, Demand, Global | — |
| **Features** | Full TDS-007 vector incl. futures | Spot-only subset | — |
| **MI** | 6-agent snapshot, B/R/N scores | DATA_DEGRADED interim publish | CURVE_BACKWARDATION regime |
| **Decision** | NHV, MSP/CCI rules | Spot-only sell/hold exploratory | Hold-to-curve, full basis |
| **Promotion** | G1–G4, G6–G7 with licensed data | G2 replay on spot snapshot | G3/G4/G6 without futures |

---

## 11. Traceability

| Section | Source |
|---------|--------|
| DS-001 vendor paths | DS001_FUTURES_VENDOR_DECISION.md §6 |
| Gates G3/G6 | TDS-007 §9 |
| Hold-to-curve | TDS-008 §10.2, FD-003 |
| Required agents | TDS-009 §4.1, §9 |
| Futures agent failure | TDS-004 §4.5 |
| Basis mitigation | FD-030, REQ-133 |

---

*End of futures dependency analysis.*
