# Non-Functional Requirements

**Source of truth:** `KrishiNetra_Founder_Thesis_Product_Spec_v5.docx` (v5.0)

NFRs extracted from trust framework (§14), validation (§17), agentic rules (§9), forecasting philosophy (§13), risks (§21), and operational notes (§22).

---

## Explainability

| NFR ID | Requirement | Source | Priority |
|--------|-------------|--------|----------|
| NFR-EXP-001 | Every recommendation must explain **Why?** | §14 | Must |
| NFR-EXP-002 | Every recommendation must state **what could go wrong** | §14 | Must |
| NFR-EXP-003 | Every recommendation must identify **which assumptions matter** | §14 | Must |
| NFR-EXP-004 | Explainability Agent is the **only** component that converts structured signals into human-readable sentences | §9 | Must |
| NFR-EXP-005 | Conversation Agent provides NL Q&A **over the explanation**, not over raw model internals | §9 | Must |
| NFR-EXP-006 | Decision outputs always include **reasoning** alongside net value after carry | §8 | Must |
| NFR-EXP-007 | Market Intelligence provides bullish/bearish factors and supply/demand analysis for independent engine validation | §7 | Must |

**Implicit:** Explanation must not alter deterministic recommendation (follows from TC-001).

**Open:** Trust score display granularity (OQ-002) affects explainability presentation, not core NFR-EXP-001–003 content.

---

## Auditability

| NFR ID | Requirement | Source | Priority |
|--------|-------------|--------|----------|
| NFR-AUD-001 | Decision layer consumes **structured data only**—no free text from domain agents | §9 | Must |
| NFR-AUD-002 | Every domain signal includes **as-of timestamp** | §9 | Must |
| NFR-AUD-003 | Named decision rules (e.g., MSP/CCI floor) are **explicit** in deterministic Decision layer, not embedded opaquely in forecast model | §8 | Must |
| NFR-AUD-004 | Recommendation is **net-of-carry math plus named rules**, not LLM judgment | §8 | Must |
| NFR-AUD-005 | Agent separation by signal domain preserves **transparency** of concerns | §9 | Must |

---

## Traceability

| NFR ID | Requirement | Source | Priority |
|--------|-------------|--------|----------|
| NFR-TRC-001 | System can reconstruct **exactly** what would have been recommended on any **past date** given same data-as-of-date | §9, §17 | Must |
| NFR-TRC-002 | Backtest trustworthy only if historical recommendations match live logic (deterministic path) | §17 | Must |
| NFR-TRC-003 | Structured signal contract enables tracing recommendation to contributing domains (value, direction, magnitude, confidence) | §9 | Must |
| NFR-TRC-004 | Outcome tracking links sessions to realized results for calibration | §14, §18 | Must |

---

## Reproducibility

| NFR ID | Requirement | Source | Priority |
|--------|-------------|--------|----------|
| NFR-REP-001 | Forecast is a **deterministic model** output, not LLM-generated | §9 | Must |
| NFR-REP-002 | Sell/hold math is a **pure function** of data-as-of-date and user context | §9 | Must |
| NFR-REP-003 | Deterministic core isolated from LLM explanation layer | §16 v5 | Must |
| NFR-REP-004 | Eight-agent system must not become **non-reproducible** (explicit risk mitigation) | §21 | Must |
| NFR-REP-005 | Same data refresh produces **same shared** Market Intelligence for all users | §7, §9 | Must |

---

## Trust

| NFR ID | Requirement | Source | Priority |
|--------|-------------|--------|----------|
| NFR-TRS-001 | Trust components: **calibration, stability, data quality, transparency, outcome tracking** | §14 | Must |
| NFR-TRS-002 | Recommendations promoted only after demonstrating **consistent net value added** in backtest | §17 | Must |
| NFR-TRS-003 | **Conservative defaults** to mitigate trust loss after bad calls | §21 | Must |
| NFR-TRS-004 | **Stability** is an explicit evaluation dimension alongside calibration | §13, §14 | Must |
| NFR-TRS-005 | Calibration improves via flywheel: context → recommendation → outcome → calibration → trust → usage | §18 | Must |
| NFR-TRS-006 | Futures-curve benchmark sets trust bar before UX scale-out | §21 mitigation | Must |

**Implicit:** Over-reliance risk if trust display is too confident (§22 OQ-002)—NFR pending UI decision.

---

## Reliability

| NFR ID | Requirement | Source | Priority |
|--------|-------------|--------|----------|
| NFR-REL-001 | Intelligence engine must function for Market Intelligence **without user registration** (validation path) | §7 | Must |
| NFR-REL-002 | System tolerates public data lag/gaps via **basis modeling and futures feed** | §21 | Should |
| NFR-REL-003 | Recommendation updates: **daily data cadence** (working answer); flips gated by stability on material signal movement | §22 | Should (pending field test) |
| NFR-REL-004 | Partial-sell defaults improve actionability under liquidity constraints | §21 | Should |

**Note:** Spec does not define SLA, uptime %, or RPO/RTO—those are **not** founder-specified NFRs.

---

## Scalability

| NFR ID | Requirement | Source | Priority |
|--------|-------------|--------|----------|
| NFR-SCL-001 | Market Intelligence precomputed **once per data refresh**, shared across all users—**zero marginal cost per user** for MI | §7, §9 | Must |
| NFR-SCL-002 | Per-user Decision mode limited to **net-of-carry math + one explanation pass** | §9 | Must |
| NFR-SCL-003 | Architecture **commodity-configurable** to extend by commodity without redesigning core pattern | §11, §16 | Must |
| NFR-SCL-004 | Agentic design **cheap to extend by commodity** via domain separation | §9 | Should |

**Implicit:** Free farmer tier at scale requires CC-001/CC-002 cost constraints.

---

## Calibration (Evaluation NFR)

| NFR ID | Requirement | Source | Priority |
|--------|-------------|--------|----------|
| NFR-CAL-001 | Evaluate **directional accuracy, calibration, stability, decision value added** | §13 | Must |
| NFR-CAL-002 | **Decision value added** is primary metric; accuracy is secondary | §13 | Must |
| NFR-CAL-003 | Benchmark strategies: (1) sell immediately, (2) hold to futures curve, (3) KrishiNetra | §17 | Must |
| NFR-CAL-004 | All comparisons on **net value after carry** | §17 | Must |
| NFR-CAL-005 | Low-accuracy model that beats curve after costs is useful; high-accuracy that does not beat curve is not | §13 | Must |

---

## Regulatory & Safety (Trust-Adjacent)

| NFR ID | Requirement | Source | Priority |
|--------|-------------|--------|----------|
| NFR-REG-001 | Product must not drift into **registrable investment advice** | §21 | Must (legal) |
| NFR-REG-002 | Financing features require **NBFC/RBI** awareness when introduced | §21 | Must (Phase 5+) |

---

## Implicit NFRs (Derived, Not New Requirements)

| NFR ID | Implicit requirement | Basis |
|--------|---------------------|-------|
| NFR-IMP-001 | LLM outputs must be **non-authoritative** for numeric decisions | §9 boundary |
| NFR-IMP-002 | Signal freshness must align with daily cadence and as-of timestamps | §9, §22 |
| NFR-IMP-003 | Market Intelligence and Decision modes may share forecast core but differ in user context application | §7, §8 |

---

## NFR Category Summary

| Category | Count (Must) | Open gaps |
|----------|--------------|-----------|
| Explainability | 7 | Display format (OQ-002) |
| Auditability | 5 | MSP "near floor" threshold (OQ-005) |
| Traceability | 4 | Outcome capture mechanism (OQ-007) |
| Reproducibility | 5 | — |
| Trust | 6 | Promotion threshold (OQ-008) |
| Reliability | 4 | Update/stability field testing (OQ-001) |
| Scalability | 4 | — |
| Calibration | 5 | — |
| Regulatory | 2 | Legal review (OQ-009) |

---

## NFR Verification Hooks (For Later Phases—Not Architecture)

Founder spec implies verification via:

- §17 backtest (reproducibility, trust promotion)
- §14 trust components (calibration, stability, outcome tracking)
- §7 Market Intelligence without adoption (engine validation)

No implementation methods specified in v5.
