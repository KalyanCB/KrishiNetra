# DS-001 — Founder Decision Package (Commercial Futures Feed)

**Date:** 2026-06-04  
**PI:** PI3 Track F (KDO — research only, no new vendor research)  
**Decision ID:** DS-001  
**Requirement:** REQ-071 (commercial futures feeds), DD-005, DA-002  
**Status:** **FOUNDER DECISION REQUIRED** — no executed NDU/vendor contract on file  

**Inputs (synthesis only):** [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md), [FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md)

---

## 1. Decision Question

Approve the **recommended primary and fallback paths** for Phase 1 **NCDEX KAPAS EOD** futures ingest (REQ-071), and authorize **Year 1 budget planning** and **vendor RFP**, so production futures ingest (E-03) and hold-to-curve DVA bake-off (E-06) can proceed after contract execution?

---

## 2. Recommendation (for approval)

| Path | Description |
|------|-------------|
| **Primary** | **NCDEX KAPAS EOD** via an **NCDEX-authorized EOD/delayed domestic vendor** (shortlist: Accelpix, Accord Fintech, Global Financial Datafeeds). Scope: KAPAS futures + OI for curve/basis features; **EOD or 20-min delayed** (not L1 real-time). Written **non-display sublicense** for backend ingest. |
| **Fallback** | **Direct NCDEX NDU — EOD Bhav Copy** (~₹15,000/year domestic tariff) + in-house UDiFF/CSV ingest until vendor API contract is executed. |
| **Sprint 0 / dev only** | Public NCDEX bhav download **only** with explicit founder/legal waiver — **not** REQ-071 production. |
| **Deferred Phase 1** | Bloomberg/Refinitiv-class terminals, NCDEX/MCX **real-time** direct feeds, **MCX dual-exchange** integration. |

**Venue:** NCDEX primary (KAPAS / cotton complex); MCX secondary — monitor only, no dual-integrate in Phase 1.

**Year 1 budget (planning, vendor path):** **₹3–8 lakhs** all-in (vendor + exchange pass-through + legal). **Fallback direct NDU:** ~**₹15k/year** exchange tariff + internal ops.

---

## 3. Costs (order of magnitude)

*Binding quotes require RFP; figures below are from existing research only.*

| Option | Annual cost (OM) | Phase 1 fit |
|--------|------------------|-------------|
| **Primary — authorized domestic vendor (EOD API)** | **₹0.05–0.2M** vendor list tiers + exchange pass-through; **₹3–8L Y1 all-in** (planning) | **Recommended** |
| **Fallback — NCDEX direct EOD NDU** | **~₹15k/yr** domestic bhav copy; **₹0.015–0.5M** if broader EOD bundles | **Lowest cost production path** |
| NCDEX direct (20 min delayed) | ~₹25k/yr | Optional tier; not required (DA-008 daily) |
| NCDEX/MCX real-time L1 | **₹2M–4.5M+** | **Out of scope** Phase 1 |
| MCX direct EOD | **₹0.015–0.5M+** (+ connectivity for RT) | **Deferred** — dual stack |
| Bloomberg / Refinitiv enterprise | **$10k–100k+** | **Deferred** Phase 1 |
| Public bhav / TradingView delayed | **₹0** | **Not production** (REQ-071) |

---

## 4. Licensing

| Topic | Requirement |
|-------|-------------|
| **Production (REQ-071)** | Exchange **NDU** (Non-Display Usage) or **authorized vendor sublicense** — not REQ-070 public scraping |
| **Primary path** | Vendor holds NCDEX authorization; KrishiNetra needs **written non-display sublicense** for backend ingest (`source=futures_feed`, `exchange=NCDEX`) |
| **Fallback path** | Direct **NCDEX NDU — EOD Bhav Copy** agreement; annual advance billing per exchange tariffs |
| **Prohibited for prod** | Unlicensed portal scrape; NCDEX academic 2 GB research policy; TradingView free delayed charts without redistribution deal |
| **Display / redistribution** | Separate exchange rules; backend algo use triggers non-display fees |
| **Blocks removed when** | Signed NDU **or** vendor sublicense on file **and** founder approval recorded |

---

## 5. Benefits (if approved and contracted)

| Area | What unlocks |
|------|----------------|
| **REQ-071 / DD-005** | Licensed commercial futures ingest for production |
| **TDS-007 features** | `curve_slope`, `curve_level_near`, `open_interest_change`, `basis_futures_spot`, `carry_implied_30/60/90` |
| **FD-003 / REQ-082** | Hold-to-futures-curve benchmark and credible DVA vs curve |
| **FD-030 / REQ-133** | Full basis modeling (concurrent licensed futures + mandi spot) |
| **TDS-007 gate G6** | Futures + Market agents ≥ 99% days (with reliable EOD SLO) |
| **TDS-009** | Cotton registry `required_agents: [Market, Futures]` — production MI path |
| **E-03 / E-06** | Production futures ingest; licensed-track promotion gates G3/G4/G6 |
| **DA-008 alignment** | Daily EOD batch sufficient; no ₹20L+ real-time license needed |

**Without licensed feed (per dependency analysis):** Schema and spot-only research continue; **production-grade DVA, G6, basis/curve features, and FD-003 benchmark remain blocked.**

---

## 6. Alternatives Considered

| Alternative | Verdict | Reason |
|-------------|---------|--------|
| NCDEX KAPAS EOD via authorized vendor | **Primary** | Low–medium integration; single venue; matches DA-008 and Track C “one aggregator” |
| NCDEX direct EOD NDU | **Fallback** | Lowest cost; ops owns file delivery; satisfies REQ-071 when executed |
| MCX parallel (Kapas/Cotton) | **Deferred** | Dual compliance and cost; NCDEX sufficient Phase 1 |
| NCDEX/MCX real-time L1 | **Deferred** | DA-008 daily batch; disproportionate cost |
| Bloomberg / Refinitiv | **Deferred** | Cost and integration vs cotton-only daily MI |
| Public bhav / delayed UI feeds | **Dev only** | Not REQ-071; legal waiver required |
| Spot-only MI without futures | **Not production** | Exploratory pipeline only; G3/G4/G6 and FD-003 blocked |

---

## 7. Risks and Dependencies

| Risk | Severity | Note |
|------|----------|------|
| Thin KAPAS OI | Medium | Use `futures_feed_ok` + confidence penalties |
| Sublicense terms / RFP variance | Medium | Written non-display scope required |
| UDiFF migration gaps (Jul 2024) | Low–Medium | Parser/backfill validation |
| False promotion on spot-only DVA | **High** | Gates G3/G4/G6 block without licensed feed |
| Indefinite deferral of DS-001 | **High** | REQ-071, DD-005, FD-003 production blocker |

**Parallel work allowed:** E-01 S07/S09/S11, Agmarknet/weather/policy ingest, Futures Agent stub/degraded mode — **do not** treat spot-only DVA as production promotion.

---

## 8. Founder Decision

**Instructions:** Select one option. Record decision, name, and date in the table below (or commit to repo per program convention).

### Option A — **APPROVE** (recommended paths + budget band)

- [ ] I approve **Primary:** NCDEX KAPAS EOD via NCDEX-authorized domestic vendor (EOD/20-min delayed; shortlist Accelpix, Accord, GDF).
- [ ] I approve **Fallback:** Direct NCDEX NDU EOD Bhav Copy if vendor contract slips.
- [ ] I approve **Sprint 0 dev-only** public bhav with legal waiver (non-REQ-071, no user-facing MI until NDU).
- [ ] I approve **Year 1 budget planning band:** ₹3–8 lakhs all-in (vendor path); ~₹15k/yr reference for direct NDU fallback.
- [ ] I authorize **RFP to 2–3** NCDEX EOD authorized vendors and **parallel NDU quote** for fallback pricing.
- [ ] I confirm **deferred for Phase 1:** Bloomberg/Refinitiv, MCX dual-exchange, real-time L1.

### Option B — **REJECT**

- [ ] I reject the recommendation above. **Do not** proceed with vendor RFP or NDU on these terms.

**If reject — required:** Brief rationale and preferred direction (e.g. defer all commercial futures, alternate venue, different budget cap).

| Field | Record here |
|-------|-------------|
| **Decision** | ☐ APPROVE (Option A) &nbsp;&nbsp; ☐ REJECT (Option B) |
| **Founder name** | |
| **Date** | |
| **Notes / modifications** | |

---

## 9. Post-Decision Program Actions

| # | Action | Owner | Trigger |
|---|--------|-------|---------|
| 1 | Issue RFP (KAPAS EOD + OI, sublicense, SLA) | Program / Ops | **APPROVE** |
| 2 | Quote NCDEX direct NDU EOD (fallback) | Ops | **APPROVE** |
| 3 | Execute NDU or vendor sublicense | Ops / Legal | After vendor selection |
| 4 | Unblock E-03 `futures_feed` ingest + `futures_feed_ok` | E-03 | Contract on file |
| 5 | Run E-06 licensed-track bake-off (G3/G4/G6) | E-06 | Licensed feed live |
| 6 | Revisit MCX Cotton liquidity | Product | Post-launch / Phase 7 prep |

---

## 10. Resolution Record

| Field | Value |
|-------|-------|
| **Decision ID** | DS-001 |
| **Recommendation** | Primary: NCDEX EOD via authorized vendor; Fallback: direct NCDEX EOD NDU |
| **Founder decision** | **PENDING** |
| **Contract on file** | **No** |
| **Unblocks when** | APPROVE recorded **and** signed NDU/sublicense |
| **Still blocks until contract** | E-03 production futures ingest; E-06 hold-to-curve promotion |

---

## 11. Traceability

| Topic | Source |
|-------|--------|
| Vendor options, costs, licensing | DS001_FUTURES_VENDOR_DECISION.md §3–§6 |
| DVA / gates / dependency classification | FUTURES_DEPENDENCY_ANALYSIS.md §2–§10 |
| Founder benchmarks FD-003, FD-030 | FUTURES_DEPENDENCY_ANALYSIS.md §3 |
| REQ-071, DA-008, TDS-007 G6 | DS001_FUTURES_VENDOR_DECISION.md §2 |

---

## 12. Document Control

| Field | Value |
|-------|-------|
| Author | KDO PI3 Track F |
| Type | Founder decision package (research synthesis) |
| Next update | After founder sign-off and/or contract execution |

---

*End of DS-001 founder decision package.*
