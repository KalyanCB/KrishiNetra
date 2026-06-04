# DS-001 — Founder Memo: Futures Feed (One Page)

**Date:** 2026-06-04 · **PI:** PI4 Track G (KDO — docs only; no new vendor research)  
**Decision ID:** DS-001 · **Requirement:** REQ-071, DD-005, DA-002, FD-003, FD-030  
**Status:** **FOUNDER DECISION REQUIRED** — no NDU/vendor contract on file  
**Inputs (synthesis only):** [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md), [FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md)

---

## Decision

Choose whether Phase 1 proceeds **without a licensed commercial futures feed** or **acquires** one (vendor EOD API or direct NCDEX NDU EOD bhav).

| | **OPTION A — Proceed without futures** | **OPTION B — Acquire feed** |
|---|------------------------------------------|-----------------------------|
| **Cost** | **₹0** exchange/vendor OPEX; engineering continues on spot/weather/policy only. Hidden cost: deferred production MI and re-work if futures added later. | **₹3–8L Y1 all-in** (authorized domestic vendor, planning band) **or** **~₹15k/yr** direct NCDEX EOD NDU fallback + internal ingest ops. Real-time / dual-exchange / Bloomberg-class **out of scope** Phase 1. |
| **Benefits** | Unblocks **no cash contract** now; E-01 schema, Agmarknet MI, weather/policy ingest, Futures Agent **stub/degraded** mode, spot-only forecast **research** and pipeline bake-off (G1/G2). | Satisfies **REQ-071**; unlocks `curve_*`, `basis_*`, OI/carry features; **FD-003** hold-to-curve benchmark; **FD-030** full basis; TDS-007 **G6**; TDS-009 cotton `required_agents: [Market, Futures]` production path; E-03 production ingest; E-06 licensed-track promotion (G3/G4/G6). |
| **Risks** | **High:** false production promotion on spot-only DVA; **REQ-082 / FD-003** benchmark undefined; G3/G4/G6 **blocked**; MI publish blocked or permanently degraded; Agmarknet lag mitigation (FD-030) incomplete; indefinite DS-001 deferral blocks REQ-071/DD-005. **Medium:** thin KAPAS narrative without curve context. | **Medium:** RFP/sublicense variance, thin KAPAS OI (mitigate via `futures_feed_ok` + confidence penalties). **Low–Medium:** UDiFF parser/backfill. Contract execution lag until NDU/sublicense on file. |
| **Impact** | Phase 1 ships **exploratory** intelligence only — **not** production-grade DVA or cotton registry full MI. Parallel engineering allowed; **do not** treat spot-only DVA as production promotion. | Phase 1 can credibly prove DVA vs hold-to-curve and run licensed E-03/E-06 gates after contract + ingest SLO. Primary: NCDEX KAPAS EOD via authorized vendor; fallback: direct NDU EOD bhav. Dev-only public bhav requires separate legal waiver (non-REQ-071). |

---

## Recommendation (research synthesis)

**OPTION B** — acquire licensed NCDEX KAPAS EOD (vendor primary, ~₹15k/yr NDU fallback). DA-008 daily batch is sufficient; real-time not required. OPTION A is viable only for **engineering/research** with explicit non-production guardrails.

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

*Synthesis traceability: DS001_FUTURES_VENDOR_DECISION.md §3–§6; FUTURES_DEPENDENCY_ANALYSIS.md §2–§10.*
