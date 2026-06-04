# DS-001 — Founder Memo: Futures Feed (One Page)

**Date:** 2026-06-04 · **PI:** PI5 Track G (KDO — synthesis only; no new vendor research)  
**Decision ID:** DS-001 · **Requirement:** REQ-071, DD-005, DA-002, FD-003, FD-030  
**Status:** **FOUNDER DECISION REQUIRED** — no NDU/vendor contract on file  
**Inputs (synthesis only):** [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md), [FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md), [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md), [AGMARKNET_PRODUCTION_ONBOARDING.md](./AGMARKNET_PRODUCTION_ONBOARDING.md), E-02 cotton registry @ v1.0.0 active

---

## Decision

Choose whether Phase 1 proceeds **without a licensed commercial futures feed** or **acquires** one (vendor EOD API or direct NCDEX NDU EOD bhav).

| | **OPTION A — Proceed without futures** | **OPTION B — Acquire feed** |
|---|------------------------------------------|-----------------------------|
| **Cost** | **₹0** exchange/vendor OPEX; engineering continues on spot/weather/policy only. Hidden cost: deferred production MI and re-work if futures added later. | **₹3–8L Y1 all-in** (authorized domestic vendor, planning band) **or** **~₹15k/yr** direct NCDEX EOD NDU fallback + internal ingest ops. Real-time / dual-exchange / Bloomberg-class **out of scope** Phase 1. |
| **Benefits** | Unblocks **no cash contract** now; Agmarknet MI, weather/policy ingest, Futures Agent **stub/degraded** mode, spot-only forecast **research** (G1/G2). | Satisfies **REQ-071**; unlocks `curve_*`, `basis_*`, OI/carry; **FD-003** hold-to-curve benchmark; **FD-030** full basis; TDS-007 G6; cotton `required_agents: [Market, Futures]` production path; E-03 futures prod ingest; licensed DVA (G3/G4/G6). |
| **Risks** | **High:** false production promotion on spot-only DVA; **REQ-082 / FD-003** undefined; G3/G4/G6 **blocked**; strict MI publish blocked (Futures in `required_agents[]`). Agmarknet lag mitigation (FD-030) incomplete without curve. **Medium:** thin KAPAS narrative. | **Medium:** RFP/sublicense variance, thin KAPAS OI (`futures_feed_ok` + confidence penalties). **Low–Medium:** UDiFF parser/backfill. Contract lag until NDU/sublicense on file. |
| **Impact** | Phase 1 **exploratory** only — **not** production-grade DVA or full cotton MI. **Do not** treat spot-only DVA as production promotion. | Phase 1 can prove DVA vs hold-to-curve and run licensed E-03/E-06 gates after contract + ingest SLO. Primary: NCDEX KAPAS EOD via authorized vendor; fallback: direct NDU EOD bhav. |

---

## Recommendation (PI5 synthesis)

| Verdict | Option |
|---------|--------|
| **GO** | **OPTION B** — acquire licensed NCDEX KAPAS EOD (vendor primary; ~₹15k/yr NDU fallback) |
| **NO-GO** | **OPTION A** for production MI, DVA Track B, or cotton registry full intelligence path |

**Why (disk state @ PI5):** Cotton v1.0.0 active registry lists **`required_agents: Market, Futures`** (Futures weight **0.25**). [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) caps Futures confidence at **≤0.35** when feed degraded and **blocks strict MI publish** when Futures is absent from required agents; hold-to-curve (FD-003) is undefined without a licensed curve. [AGMARKNET_PRODUCTION_ONBOARDING.md](./AGMARKNET_PRODUCTION_ONBOARDING.md) confirms Agmarknet E-03 Sprint 0 is **independent** of futures — spot ingest can start, but REQ-071 futures prod ingest and FD-030 basis fallback remain **blocked until DS-001 closes**. DA-008 daily EOD batch is sufficient; real-time not required.

**OPTION A** remains acceptable **only** for parallel engineering/research with explicit non-production guardrails.

---

## PI5 — Decision gate status

| Item | Status |
|------|--------|
| **Decision status** | **OPEN** — memo updated PI5 Track G; founder signature still required |
| **KDO recommendation** | **GO on OPTION B** · **NO-GO on OPTION A** (production path) |
| **E-03 consequences** | **Without B:** Sprint 0 Agmarknet + weather may proceed; **futures production ingest blocked** (REQ-071). **With B:** authorize vendor/NDU path; unblocks E-03 futures prod after contract on file + UDiFF ingest SLO. |
| **E-04 consequences** | **Without B:** Market/Weather/Policy agents runnable on observations; Futures emits **degraded** signal only; **strict MI / production promotion blocked** per TDS-009. **With B:** full five-agent runtime per SIGNAL_ENGINE_V1; unblocks E-04 → E-05 MI aggregation on licensed path. |
| **Founder action required** | (1) Sign **OPTION B** below. (2) Choose path: vendor EOD API **or** direct NCDEX NDU EOD. (3) Authorize Y1 budget band. (4) Execute NDU/sublicense so engineering has contract on file before treating futures ingest as production-ready. |

---

## Founder sign-off

| Field | Record |
|-------|--------|
| **Decision** | ☐ OPTION A (without futures) &nbsp;&nbsp; ☐ OPTION B (acquire feed) |
| **If B — path** | ☐ Vendor EOD API &nbsp;&nbsp; ☐ Direct NCDEX NDU EOD |
| **Y1 budget authorized (if B)** | ☐ ₹3–8L vendor band &nbsp;&nbsp; ☐ ~₹15k NDU fallback |
| **Founder / date** | |
| **Notes** | |

**Unblocks when (B only):** decision recorded **and** signed NDU or vendor sublicense on file.

---

*Synthesis traceability: DS001_FUTURES_VENDOR_DECISION.md §3–§6; FUTURES_DEPENDENCY_ANALYSIS.md §2–§10; SIGNAL_ENGINE_V1.md §6; AGMARKNET_PRODUCTION_ONBOARDING.md §9; E02_COMPLETION_REPORT cotton v1.0.0.*
