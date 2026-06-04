# Futures Signal Prototype — Public/EOD Data Path Assessment

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI9 (KDO — research only; no code) |
| **Epic** | E-04 — Futures Agent (`F-04-05`) prototype ingest |
| **Scope** | Engineering feasibility of three **non-licensed** futures data paths for cotton/KAPAS signal development |
| **Out of scope** | Production licensing decision (DS-001), vendor RFP, ingest implementation |
| **Status** | Research complete — **prototype path recommended with guardrails** |
| **Inputs** | [DS001_FOUNDER_DECISION_PACKAGE.md](./DS001_FOUNDER_DECISION_PACKAGE.md), [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md), [SIGNAL_READINESS_RECHECK.md](./SIGNAL_READINESS_RECHECK.md), [FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md), [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md), `cotton.json` @ v1.0.0 |

---

## 1. Executive Summary

KrishiNetra cotton registry requires **`required_agents: ["Market", "Futures"]`** with Futures weight **0.25** ([`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json)). DS-001 remains **OPEN** — no NDU/vendor contract on file — which today blocks **production** futures ingest (REQ-071) and **strict MI publish** ([DS001_FOUNDER_DECISION_PACKAGE.md](./DS001_FOUNDER_DECISION_PACKAGE.md) §E-04 consequences; [SIGNAL_READINESS_RECHECK.md](./SIGNAL_READINESS_RECHECK.md) §5.2).

This memo evaluates whether **public/EOD prototype paths** can unblock **E-04 enhanced degraded mode** — real `curve_slope`, `basis_futures_spot`, and OI transforms on observations — **without** treating the result as licensed production data.

| Source | Prototype verdict | Production substitute? |
|--------|-------------------|------------------------|
| **Yahoo Finance** | **Not recommended** | **No** — wrong venue/instrument; ToS/compliance risk |
| **MCX EOD Bhavcopy** | **Secondary fallback only** | **No** — deferred venue per DS-001; same legal gap as NCDEX public |
| **NCDEX EOD Bhavcopy (public)** | **Recommended prototype path** | **No** — dev-only until NDU; same parser as ~₹15k/yr licensed path |

| Decision | Recommendation |
|----------|----------------|
| **DS-001 downgrade (Phase-1 blocker → production-only blocker)?** | **YES — with guardrails** (§7) |
| **Best prototype source** | **NCDEX public EOD bhavcopy** (UDiFF CSV/XLS) |

**Honest ceiling:** None of these paths replace licensed NDU/vendor feed for REQ-071, DVA Track B (G3/G4/G6), hold-to-curve (FD-003/REQ-082), or strict MI production promotion. They exist to **exercise FuturesSignalGenerator math**, AC harness, and SignalSnapshot assembly on **real KAPAS curve observations** before founder budget executes.

---

## 2. Evaluation Framework

Each path is scored against E-04 Futures Agent needs ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §6):

| Need | Prototype requirement |
|------|----------------------|
| Near/far contract settle | `curve_slope`, `curve_level_near`, `carry_implied_*` |
| Open interest / volume | `open_interest_change`; thin-OI penalties |
| Concurrent spot | Agmarknet modal for `basis_futures_spot` (FD-030) |
| Feed health flag | `futures_feed_ok=false` for all paths in this memo |
| Confidence | Cap **≤ 0.35** when degraded ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §6.5) |

**Parse/integration complexity (1–5):** 1 = drop-in API; 5 = brittle scraper + heavy normalization.

**Licensing risk:** Separate columns for **prototype (engineering)** vs **production (REQ-071)**.

---

## 3. Path 1 — Yahoo Finance

### 3.1 Availability & access method

| Dimension | Assessment |
|-----------|------------|
| **Indian KAPAS** | **Not available.** Yahoo Finance market-coverage tables list US/global exchanges (CBOT, ICE, NYMEX, etc.) with ICE Data Services delays; **NCDEX is not listed** ([Yahoo Finance exchange coverage](https://help.yahoo.com/kb/finance-for-web/SLN2310.html)). No `NCDEX:KAPAS` or `SHANKRKPAS` ticker exists on the platform. |
| **US cotton proxy** | **ICE cotton #2** `CT=F` (continuous) or month codes (e.g. `CTK26`) — **30-minute delayed** ICE Futures US per Yahoo coverage table. |
| **Access** | Unofficial `yfinance` / query endpoints scraping `finance.yahoo.com` — **not** a supported commercial API; Yahoo terminated official Finance API and restricts automated access ([Stack Overflow / Yahoo confirmation](https://stackoverflow.com/questions/47064776)). |
| **Reliability** | **Low–Medium** for prototypes — endpoint/schema changes without notice; rate limits; no SLA; frequent breakages reported by community libraries. |

### 3.2 Cotton/KAPAS contract coverage

| Item | Yahoo | KrishiNetra need |
|------|-------|------------------|
| Venue | ICE/CME US | **NCDEX** (primary per [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md) §3) |
| Instrument | US cotton #2 (lbs, USD) | **Shankar KAPAS** (₹/20 kg, Rajkot basis, 4 MT lot) |
| Curve months | US monthly chain | NCDEX **Nov / Feb / Apr** seasonal launches |
| OI | Available on US contracts | Needed for KAPAS; **wrong market** |
| Basis vs Agmarknet | FX + lint vs kapas basis error | **Not comparable** to TG/MH mandi modal (₹/quintal) |

**Conclusion:** Yahoo provides at best a **global cotton sentiment proxy**, not a KAPAS curve. Using `CT=F` for Indian farmer MI would mis-state basis, carry, and regime detection (`CURVE_BACKWARDATION` per TDS-009).

### 3.3 Latency & historical depth

| Dimension | Value |
|-----------|-------|
| **Latency** | 10–30 min delayed (US futures); irrelevant for DA-008 daily EOD batch |
| **Historical depth** | Decades for `CT=F` via unofficial download — **wrong instrument** |
| **EOD alignment** | Adjusted continuous series ≠ exchange official settle used in DVA backtest ([DVA_BACKTEST_PREPARATION.md](./DVA_BACKTEST_PREPARATION.md) §4 — no revised history) |

### 3.4 Parse/integration complexity

**Score: 2/5** technically (pandas + `yfinance`), **5/5 effective** after normalization — must bolt FX, unit conversion (lbs→quintal), and explicit **non-KAPAS** labeling to avoid silent wrong signals.

### 3.5 Licensing / compliance risk

| Mode | Risk | Rationale |
|------|------|-----------|
| **Prototype** | **High** | Yahoo ToS / API ToU prohibit commercial/backend derive-income use and redistribution ([Yahoo API Terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html)). Scraping for persisted backend observations conflicts with REQ-071 spirit and DS-001 §4.5 dev-only waiver pattern. |
| **Production** | **Blocking** | Does not satisfy REQ-071, DD-005, or exchange NDU. ICE data requires ICE/authorized vendor license for commercial algo use — Yahoo display ≠ sublicense. |

### 3.6 Suitability for E-04 enhanced degraded mode

| Criterion | Verdict |
|-----------|---------|
| Exercises KAPAS curve math | **No** — wrong market |
| `basis_futures_spot` vs Agmarknet | **Misleading** |
| `futures_feed_ok` semantics | Should remain **false** |
| Global Agent overlap | USDA/ICAC already cover **world** cotton; Yahoo adds little unique signal |

**Verdict: Not suitable** for FuturesSignalGenerator prototype except optional **Global-sentiment lab** — out of scope for F-04-05 KAPAS path.

---

## 4. Path 2 — MCX EOD Bhavcopy

### 4.1 Availability & access method

| Dimension | Assessment |
|-----------|------------|
| **Portal** | Public [MCX Bhavcopy](https://www.mcxindia.com/market-data/bhavcopy) — web table + download; commodity filter includes **KAPAS**, **LONGCOTTON**, and related agro contracts. |
| **Format** | **UDiFF**-aligned bhavcopy per MCX/CCL circulars ([MCX UDiFF](https://www.mcxccl.com/circulars/unified-distilled-file-formats-(udiff))); legacy CSV/XLS variants on historical pages. |
| **Automation** | Community wrappers (e.g. `mcxlib`) hit public endpoints — **same legal posture as scripted portal download**; not REQ-071. |
| **Licensed alternative** | MCX direct datafeed / authorized vendor — separate NDU stack; **deferred Phase 1** per DS-001 (dual-exchange cost). |

### 4.2 Cotton/KAPAS contract coverage

| Product | MCX role | Notes |
|---------|----------|-------|
| **KAPAS** | Listed (`FUTCOM/KAPAS`) | Competing venue; liquidity varies vs NCDEX |
| **Cotton / LONGCOTTON** | Revised specs from Nov 2025 expiries ([MCX/TRD/306/2025](https://www.mcxindia.com) circulars cited in DS-001) | Different spec from NCDEX Shankar KAPAS |
| **Registry alignment** | **Secondary / monitor only** | [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md) §3: NCDEX KAPAS **primary**; MCX dual-integration **explicitly out of scope Phase 1** |

MCX bhavcopy **can** populate curve/OI fields, but cotton registry, DVA bake-off, and founder DS-001 recommendation all anchor on **NCDEX KAPAS**. Prototype on MCX creates **venue drift** — parser and contract calendar differ from production target.

### 4.3 Latency & historical depth

| Dimension | Value |
|-----------|-------|
| **Latency** | **EOD** — post-session file (typical ~1 business day lag for batch ingest; same class as NCDEX EOD) |
| **Historical bhav** | Portal historical bhav + date-wise tools; MCX documents **≤3 months free** on some historical tiers; deeper history via **paid** datafeed ([MCX datafeed categories](https://www.mcxindia.com/technology/datafeed/categories-of-datafeed)) |
| **Backfill for 36-mo DVA panel** | **Weaker than NCDEX public historical bhav** without paid MCX historical feed |

### 4.4 Parse/integration complexity

**Score: 3/5**

| Factor | Detail |
|--------|--------|
| UDiFF | Harmonized with NCDEX post-2024 — reusable parsing patterns |
| MCX-specific | Separate URL scheme, holiday calendar, commodity codes (`FUTCOM`) |
| Unit mapping | MCX KAPAS quotation units must be verified against contract spec sheet — may differ from NCDEX ₹/20 kg |
| Roll logic | MCX month codes ≠ NCDEX Nov/Feb/Apr cycle — **second mapping table** |

Building MCX prototype **before** NCDEX parser duplicates effort that production will not use (DS-001 defers MCX).

### 4.5 Licensing / compliance risk

| Mode | Risk | Rationale |
|------|------|-----------|
| **Prototype** | **Medium–High** | MCX terms: website data **delayed**; automated harvest of bhav for commercial backend mirrors NCDEX public-bhav analysis — **dev-only with founder/legal waiver** ([DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md) §4.5, [FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md) §4.1). |
| **Production** | **Blocking** | Requires MCX datafeed agreement + non-display fees; **not** the Phase 1 primary path. |

### 4.6 Suitability for E-04 enhanced degraded mode

| Criterion | Verdict |
|-----------|---------|
| Real OI/curve transforms | **Yes** — technically |
| Registry venue match | **No** — NCDEX primary |
| Production parser reuse | **Low** — second exchange stack |
| Dual-source confusion | Risk of promoting MCX curve as KAPAS MI |

**Verdict: Secondary fallback** if NCDEX public bhav is temporarily unavailable — **not** preferred prototype path.

---

## 5. Path 3 — NCDEX EOD Bhavcopy (public)

### 5.1 Availability & access method

| Dimension | Assessment |
|-----------|------------|
| **Portal** | [NCDEX Bhav Copy](https://ncdex.com/index.php/markets/bhavcopy) — date picker; **UDiFF CSV/XLS from 2024-07-08**; pre-UDiFF historical section through 2024-07-05. |
| **Licensed twin** | **Direct NCDEX NDU EOD Bhav Copy ~₹15k/yr** delivers the **same file class** via authorized channel ([NCDEX tariffs](https://ncdex.com/tech/tariffs)) — prototype parser **transfers to production** with contract swap only. |
| **Vendor path** | Authorized EOD API (Accelpix, Accord, GDF) — production primary; **superset** of public fields when sublicensed. |
| **Automation** | Scheduled HTTPS download + UDiFF parser — engineering pattern already assumed in DS-001 fallback ([DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md) §6.2). |

### 5.2 Cotton/KAPAS contract coverage

| Field | NCDEX KAPAS (Shankar) |
|-------|------------------------|
| Symbol | **KAPAS** / **SHANKRKPAS** |
| Quote | **₹ per 20 kg** ([NCDEX KAPAS product page](https://ncdex.com/index.php/products/KAPAS)) |
| Lot | **4 MT** (200 × 20 kg maunds) |
| Tick | **₹0.50** per 20 kg |
| Months | **November, February, April** (seasonal) |
| Delivery | Rajkot basis (registry-aligned Gujarat belt) |
| Bhav fields | OHLC, settle, volume, **OI**, expiry — sufficient for [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §6.2 components |
| Liquidity | **Thin OI** on active months (tens of contracts cited DS-001 §3) — expect `penalty_thin_oi` even on licensed feed |

**Legacy note:** V797 Kapas (`KAPASSRNR`) discontinued per NCDEX circulars — parser must map **current SHANKRKPAS** chain only.

### 5.3 Latency & historical depth

| Dimension | Value |
|-----------|-------|
| **Latency** | **EOD** after NCDEX session — matches DA-008 daily batch ([DS001_FOUNDER_DECISION_PACKAGE.md](./DS001_FOUNDER_DECISION_PACKAGE.md)) |
| **Historical depth** | Public **historical bhav** UI to 2024-07-05 legacy + UDiFF era — adequate for **12–36 mo** prototype backfill with gap handling around Jul 2024 format migration |
| **Deep tick/order book** | Paid NDU tiers only — **not needed** for E-04 signal components |

### 5.4 Parse/integration complexity

**Score: 3/5** (4/5 if pre-UDiFF backfill required)

| Task | Effort |
|------|--------|
| UDiFF bhav CSV parse | Medium — standardized MDAC schema ([NCDEX UDiFF guidance](https://ncdex.com/index.php/member-file/format-of-udiff-report-downloads-exchange)) |
| Contract roll / near-far | Medium — map Nov/Feb/Apr expiries to `near`/`far` for `curve_slope` |
| Unit harmonization | Medium — convert ₹/20 kg → ₹/quintal (×5) for `basis_futures_spot` vs Agmarknet modal |
| OI z-scores | Low — field present when traded; null/OI=0 on thin days |
| Quality hooks | Low — wire `futures_feed_ok=false`, `source=ncdex_public_bhav_prototype` |

This is the **same integration surface** as DS-001 Option B fallback NDU — highest engineering reuse.

### 5.5 Licensing / compliance risk

| Mode | Risk | Rationale |
|------|------|-----------|
| **Prototype (engineering)** | **Medium** — acceptable **with explicit waiver** | DS-001 §4.5 / §6.2: public bhav for **Sprint 0 / engineering unblock only**; automated scrape **not** REQ-071; founder/legal acknowledgment required ([FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md) §6). NCDEX academic 2 GB policy **not** applicable to commercial product. |
| **Production** | **Blocking without NDU** | REQ-071 requires NDU or authorized sublicense; public download **does not** satisfy DD-005 or DVA Track B ([DVA_BACKTEST_PREPARATION.md](./DVA_BACKTEST_PREPARATION.md) B-01). |

**vs licensed NDU path:** Public and NDU bhav are **identical data class**; difference is **contract + audit trail**, not math.

### 5.6 Suitability for E-04 enhanced degraded mode

| Criterion | Verdict |
|-----------|---------|
| KAPAS curve/basis/OI transforms | **Yes** — full §6.2 feature set (with thin-OI penalties) |
| Venue/registry match | **Yes** — NCDEX primary |
| Parser → production | **Yes** — NDU swap |
| `futures_feed_ok` | **false** until licensed ingest |
| Confidence cap | **≤ 0.35** per SIGNAL_ENGINE_V1 §6.5 |
| Strict MI publish | **Still blocked** — agent row present but degraded label |

**Verdict: Best prototype path** for FuturesSignalGenerator in E-04 enhanced degraded mode.

---

## 6. Comparative Matrix

| Criterion | Yahoo Finance | MCX EOD Bhav | NCDEX EOD Bhav (public) |
|-----------|---------------|--------------|-------------------------|
| **Access** | Unofficial API scrape | Public portal / UDiFF | Public portal / UDiFF |
| **KAPAS coverage** | **None** (US CT only) | KAPAS listed; **non-primary venue** | **Shankar KAPAS — primary** |
| **Latency** | 10–30 min (US) | EOD | EOD |
| **Historical depth** | Deep (wrong market) | Medium; paid for deep | **Good** public historical + UDiFF |
| **OI in file** | US only | Yes | Yes |
| **Parse complexity (1–5)** | 2 (tech) / 5 (effective) | **3** | **3** (4 w/ pre-UDiFF) |
| **Prototype legal risk** | **High** | Medium–High | **Medium** (w/ waiver) |
| **Production legal** | **Blocking** | **Blocking** (wrong path) | **Blocking w/o NDU** |
| **Production parser reuse** | None | Low | **High** |
| **E-04 degraded suitability** | **Poor** | **Secondary** | **Best** |

---

## 7. Core Decision — DS-001 Downgrade?

### 7.1 Question

Can DS-001 be **downgraded** from **Phase-1 blocker** (blocks all E-04/MI work) to **Production-readiness blocker only** (allows prototype futures ingest + degraded Futures signals using public/EOD sources)?

### 7.2 Recommendation: **YES — with guardrails**

**Rationale (disk state @ PI9):**

1. **Founder memo already allows parallel engineering.** [DS001_FOUNDER_DECISION_PACKAGE.md](./DS001_FOUNDER_DECISION_PACKAGE.md) states OPTION A is acceptable for *"parallel engineering/research with explicit non-production guardrails"* and that without Option B, *"Futures emits degraded signal only"* while Market/Weather/Policy remain runnable.

2. **PI8 recheck already separates E-04 viability from strict MI.** [SIGNAL_READINESS_RECHECK.md](./SIGNAL_READINESS_RECHECK.md) §5.1: **E-04 viable for enhanced degraded start**; strict MI **still blocked** — DS-001 listed as blocker for **production** orchestration, not agent wiring.

3. **NCDEX public bhav is an explicit DS-001 engineering fallback.** [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md) §6.2 item 2: *"Sprint 0 / engineering unblock only (non-REQ-071)"* with legal waiver — distinct from production NDU.

4. **FUTURES_DEPENDENCY_ANALYSIS** separates layers: public bhav = **DEFERRED (prod) / dev parse**; licensed NDU = production REQUIRED ([FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md) §4.1, §5 Path D).

5. **Reclassifying DS-001 does not approve OPTION A for product claims.** Production MI, DVA Track B, REQ-071 ingest, and hold-to-curve remain **blocked until founder signs OPTION B + contract on file**.

### 7.3 Guardrails (mandatory if downgrade accepted)

| # | Guardrail | Enforces |
|---|-----------|----------|
| G-01 | **`environment=prototype`** label on futures observations and StructuredSignals | No production promotion |
| G-02 | **`futures_feed_ok=false`** always for public/Yahoo/MCX-public paths | [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §6.5 degraded branch |
| G-03 | **Futures confidence cap ≤ 0.35** (+ thin-OI penalties) | DS-001 interim; no strict MI confidence inflation |
| G-04 | **`source_refs[]` tags** `ncdex_public_bhav_prototype` (or equivalent) | Lineage / replay audit |
| G-05 | **No strict MI publish** — `required_agents` gate remains **fail-closed for production** per TDS-009 §9 | Cotton registry unchanged |
| G-06 | **No DVA Track B** — G3/G4/G6, FD-003 hold-to-curve, REQ-082 benchmark **deferred** | [FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md) §4.3 |
| G-07 | **No `CURVE_BACKWARDATION` production regime** — may compute for dev logs; suppress in user-facing MI until licensed | TDS-009 §5.1 |
| G-08 | **Founder/legal one-line waiver** on file for automated NCDEX public bhav download (dev corpus only) | DS-001 §4.5 compliance |
| G-09 | **Yahoo Finance excluded** from prototype ingest (G-01–G-08 apply if ever used for Global lab only) | Wrong instrument + ToS |
| G-10 | **Production cutover = NDU or vendor sublicense on file** — flip `futures_feed_ok` only after DS-001 Option B closes | REQ-071 |

### 7.4 What remains blocked (unchanged)

| Capability | Blocker |
|------------|---------|
| REQ-071 production futures ingest | DS-001 Option B + contract |
| Strict `SignalSnapshot` → Forecast publish | TDS-009 `required_agents` + production labels |
| DVA vs hold-to-curve (G3/G4) | Licensed curve (FD-003) |
| Forecast gate G6 | Licensed feed ≥99% days |
| FD-030 full basis fallback to users | Licensed concurrent futures + mandi |
| E-03 futures **production** ingest SLO | NDU/vendor path |

### 7.5 What unblocks

| Capability | Enabled by NCDEX public prototype |
|------------|-----------------------------------|
| E-04 FuturesSignalGenerator implementation + unit tests | Real KAPAS OHLC/OI inputs |
| `curve_slope`, `basis_futures_spot`, `open_interest_change` transforms | SIGNAL_ENGINE_V1 §6.2 |
| SignalSnapshot assembly harness (degraded row) | Parallel with Market (PI8-ready) |
| E-03 ingest **design validation** (parser, roll map, unit tests) | Pre-NDU |
| Enhanced degraded E-04 end-to-end demo | Non-production label |

---

## 8. Implementation Notes (Design Only — No Code)

Recommended prototype architecture (for E-04/E-03 design docs):

```
NCDEX public bhav (UDiFF CSV)
  → parse KAPAS rows (SHANKRKPAS)
  → normalize ₹/20kg → ₹/quintal
  → near/far month selection (Nov/Feb/Apr calendar)
  → FuturesObservation (source=ncdex_public_bhav_prototype)
  → DataQualitySnapshot.futures_feed_ok=false
  → Futures Agent (confidence ≤ 0.35)
  → StructuredSignal (degraded, non-production)
```

**Do not** merge prototype observations into production DVA panels or flip registry `required_agents`.

---

## 9. Return Payload

| Field | Value |
|-------|-------|
| **Report path** | `docs/research/FUTURES_SIGNAL_PROTOTYPE.md` |
| **DS-001 downgrade** | **YES** — Phase-1 engineering blocker → **production-readiness blocker only**, subject to §7.3 guardrails |
| **Best prototype source** | **NCDEX EOD Bhavcopy (public UDiFF)** |
| **Yahoo Finance** | **Not recommended** |
| **MCX Bhavcopy** | **Secondary contingency only** |
| **Production substitute** | **None of the above** — licensed NDU/vendor per DS-001 Option B |

---

## 10. Traceability

| Section | Sources |
|---------|---------|
| Registry agents/weights | `cotton.json` v1.0.0 |
| Futures agent math | [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §6 |
| E-04 viability | [SIGNAL_READINESS_RECHECK.md](./SIGNAL_READINESS_RECHECK.md) §5 |
| DS-001 gates | [DS001_FOUNDER_DECISION_PACKAGE.md](./DS001_FOUNDER_DECISION_PACKAGE.md) |
| Vendor/public path | [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md) §4.5, §6.2 |
| DVA deferral | [FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md) |
| REQ-071 / ingest | [E03_DATA_INGESTION_READINESS.md](./E03_DATA_INGESTION_READINESS.md) §3.6 |
| External | [NCDEX Bhavcopy](https://ncdex.com/index.php/markets/bhavcopy), [NCDEX KAPAS](https://ncdex.com/index.php/products/KAPAS), [NCDEX Tariffs](https://ncdex.com/tech/tariffs), [MCX Bhavcopy](https://www.mcxindia.com/market-data/bhavcopy), [Yahoo exchange coverage](https://help.yahoo.com/kb/finance-for-web/SLN2310.html) |

---

*End of Futures Signal Prototype assessment.*
