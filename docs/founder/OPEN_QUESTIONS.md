# Open Questions

**Source of truth:** `KrishiNetra_Founder_Thesis_Product_Spec_v5.docx` (v5.0)

---

## Resolved in v5 (Documented for Traceability)

These were open in prior versions; v5 moved them into the spec. Listed here so downstream work does not re-litigate them.

| Former question | Resolution in v5 | Source |
|-----------------|------------------|--------|
| What is minimum useful accuracy? | No abstract minimum; bar is §17 backtest (decision value added vs sell-at-harvest and hold-to-curve, net of carry). | §13, §22 |
| What is update frequency? | Working answer: daily data cadence; recommendation changes gated by stability constraint (material signal movement only). Needs field testing. | §22 |
| What is the next commodity after cotton? | Structural criteria: storable + liquid futures + price-floor mechanism. Candidates: maize, soybean, turmeric (NCDEX). Mirchi explicitly excluded. | §20, §22 |

---

## Still Open (§22)

### OQ-001 — Recommendation update frequency and stability gating

| Field | Content |
|-------|---------|
| **Question** | How often should recommendations update? The spec offers a working answer (daily data cadence; call flips only on material signal movement via stability constraint) but states this **needs field testing**. |
| **Why it matters** | Too-frequent flips erode trust and appear noisy; too-infrequent flips miss actionable moves. Directly affects farmer/trader reliance and calibration interpretability. |
| **Impact** | Product UX (staleness vs churn), backtest design (when a "call" is considered changed), operational data pipeline cadence, and stability metric definition. |
| **Suggested resolution path** | Define stability metric thresholds on structured signals; run field pilots comparing user trust and outcome capture under daily refresh vs gated flip rules; document flip rate vs outcome in calibration framework (§14). |

---

### OQ-002 — Trust score display format

| Field | Content |
|-------|---------|
| **Question** | How should trust scores be displayed—a single calibrated confidence plus a short "what could go wrong," or a richer breakdown? |
| **Why it matters** | Affects trust and over-reliance. §14 requires transparency but does not specify UI/communication granularity. |
| **Impact** | Explainability Agent output shape, Conversation Agent grounding, regulatory perception (over-confidence), and adoption after wrong calls (§21). |
| **Suggested resolution path** | User research with farmers and traders on comprehension and appropriate reliance; A/B test single vs multi-factor display while holding deterministic recommendation constant; align with legal review on advice framing (§21). |

---

### OQ-003 — Financing introduction trigger

| Field | Content |
|-------|---------|
| **Question** | When should financing be introduced? Spec states: after cotton value is proven and inventory registration exists—but the **exact trigger is unresolved**. |
| **Why it matters** | Financing touches NBFC/RBI scope (§21); premature introduction adds regulatory and product complexity before core intelligence is validated. |
| **Impact** | Roadmap Phase 5 timing, entity model (Financing future entity §15), partnerships, and net-of-carry math inputs (financing profile already in §8). |
| **Suggested resolution path** | Define explicit Phase 2/3 gates: inventory registration adoption metrics, backtest promotion criteria met (§17), calibration stability thresholds (§14); legal opinion on financing-adjacent features; only then scope Phase 5 financing partnerships. |

---

## Open by Implication (Not Listed in §22 but Unspecified in Spec)

These are **not invented requirements**—they are gaps where the spec is silent. Recorded per task rules.

| ID | Question | Why it matters | Impact | Suggested resolution path |
|----|----------|----------------|--------|---------------------------|
| OQ-004 | What constitutes "material signal movement" for stability gating? | §22 references gating without definition. | Flip frequency, auditability. | Quantify per-signal delta thresholds in calibration/stability framework. |
| OQ-005 | What is "at or near" MSP floor for MSP/CCI floor rule? | §8 names rule without numeric proximity definition. | Hold calculus shape, backtest rule application. | Policy expert + historical CCI procurement windows; codify as named rule parameters. |
| OQ-006 | How is "Partial Sell" / "Partial Hold" quantity determined? | §8 lists outputs; no split logic specified. | UX, liquidity mitigation (§21). | Founder/product decision on default splits vs user-specified partial quantity. |
| OQ-007 | How are decision session outcomes captured and validated? | §18 flywheel depends on outcome capture; mechanism not specified. | Calibration, proprietary data quality. | Define outcome recording workflow and ground-truth sources in Phase 1 scope review. |
| OQ-008 | What does "consistently adds value" mean quantitatively for promotion (§17)? | Promotion gate stated without statistical threshold. | Go/no-go for public recommendation claims. | Founder sign-off on backtest windows, significance, and net-value metric definition. |
| OQ-009 | Legal classification of sell/hold guidance | §21 requires legal review; outcome not in spec. | Regulatory constraint RC-001/RC-002. | Engage counsel; document product copy and disclaimer requirements before scale. |

---

## Question Priority Matrix

| ID | Status | Urgency for Phase 1 | Blocks architecture? |
|----|--------|---------------------|----------------------|
| OQ-001 | Open (working answer) | High | Partially (cadence + stability) |
| OQ-002 | Open | Medium | Explainability presentation only |
| OQ-003 | Open | Low (Phase 5) | No for Phase 1 |
| OQ-004 | Implied gap | High | Yes for flip gating |
| OQ-005 | Implied gap | High | Yes for MSP/CCI rule |
| OQ-006 | Implied gap | Medium | Decision UX |
| OQ-007 | Implied gap | High | Flywheel / calibration |
| OQ-008 | Implied gap | High | Validation gate |
| OQ-009 | Implied gap | High | Go-to-market risk |
