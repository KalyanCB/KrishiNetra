# Story Audit — E-00, E-01, E-02

**Date:** 2026-06-03  
**Auditor:** Technical Delivery Lead  
**Scope:** Verify traceability, no new requirements, dependencies, testable AC, measurable DoD

---

## Audit Summary

| Epic | Stories | TDS trace | New reqs? | Dependencies valid? | AC testable? | DoD measurable? | Verdict |
|------|---------|-----------|-----------|---------------------|--------------|-----------------|---------|
| E-00 | 8 | Yes | No | Yes | Yes | Yes | **PASS** |
| E-01 | 11 | Yes | No | Yes | Yes | Yes | **PASS** |
| E-02 | 7 | Yes | No | Yes | Yes | Yes | **PASS** |

---

## E-00 — Program Foundation

| Story ID | TDS / ADR | New requirements? | Dependencies | AC testable | DoD measurable | Notes |
|----------|-----------|-------------------|--------------|-------------|----------------|-------|
| E-00-S01 | TDS-013 §2, ADR-001 | No | None ✓ | Yes — path manifest test | Yes — tree + no business logic | |
| E-00-S02 | TDS-013 §1, ADR-004 | No | S01 ✓ | Yes — import smoke, lockfile | Yes — install docs | |
| E-00-S03 | TDS-010 §3, TDS-003 | No | S02 ✓ | Yes — health 200 | Yes — uvicorn boots | Stub routes only |
| E-00-S04 | TDS-013 §7 | No | S02, S03 ✓ | Yes — CI green/fail | Yes — PR workflow | |
| E-00-S05 | TDS-013 §3.1, FD-006 | No | S01, S04 ✓ | Yes — negative import fixture | Yes — CI step | |
| E-00-S06 | ADR-004 | No | S03 ✓ | Yes — compose + integration skip | Yes — README 15min | |
| E-00-S07 | TDS-010 §14, TDS-012 prep | No | S03 ✓ | Yes — trace_id header tests | Yes — JSON log sample | |
| E-00-S08 | TDS-006, TDS-004 §3 | No | S02 ✓ | Yes — enum/signal validation | Yes — mypy strict shared | |

### E-00 Findings

| ID | Severity | Finding | Action |
|----|----------|---------|--------|
| E00-1 | Info | S03 creates API stubs — must not implement TDS-010 contracts yet | Enforce in review |
| E00-2 | Info | S05 depends on S04 — correct sequencing | None |

---

## E-01 — Data Foundation

| Story ID | TDS / ADR | New requirements? | Dependencies | AC testable | DoD measurable | Notes |
|----------|-----------|-------------------|--------------|-------------|----------------|-------|
| E-01-S01 | TDS-006, ADR-002 | No | E-00-S06 ✓ | Yes — alembic upgrade | Yes — migration CI | |
| E-01-S02 | TDS-006 §6–7 | No | S01 ✓ | Yes — immutability test | Yes — pattern doc | |
| E-01-S03 | TDS-006 §3.1–3.5, TDS-009 roles | No | S01, S02 ✓ | Yes — FK tests | Yes — empty tables | No seed — E-02 |
| E-01-S04 | TDS-006 §3.6–3.7, TDS-005 | No | S03 ✓ | Yes — append, partition | Yes — insert/query | |
| E-01-S05 | TDS-004, TDS-006 §3.8–3.9 | No | S03, E-00-S08 ✓ | Yes — unique, hash | Yes — 6 signals | |
| E-01-S06 | TDS-006, TDS-007, TDS-009 §7.1 | No | S05 ✓ | Yes — immutability, confidence bounds | Yes — forecast_confidence column | Not recommendation_confidence |
| E-01-S07 | TDS-006, TDS-008, TDS-009 §7.2 | No | S06, S03 ✓ | Yes — FK chain, enums | Yes — both confidence fields | |
| E-01-S08 | TDS-006 §3.17, TDS-011 | No | S03 ✓ | Yes — score bounds | Yes — linked insert | |
| E-01-S09 | TDS-006 §4, TDS-009 §8, FD-012 | No | E-00-S06, S06 ✓ | Yes — redis roundtrip | Yes — key convention | |
| E-01-S10 | TDS-006, TDS-009, ADR-003 | No | S03 ✓ | Yes — single active, schema | Yes — E-02 ready | Extends TDS-006 per ADR-003 |
| E-01-S11 | TDS-006 §5, REQ-103 prep | No | S04–S10 ✓ | Yes — integration suite | Yes — 80% persistence coverage | |

### E-01 Findings

| ID | Severity | Finding | Action |
|----|----------|---------|--------|
| E01-1 | Low | S10 adds fields beyond TDS-006 literal text | Covered by ADR-003 + TDS-009 — not new product req |
| E01-2 | Info | Explicitly excludes InventoryPosition | Correct per architecture review |
| E01-3 | Medium | OQ-004 stability_token in schema TBD | Non-blocking E-01; nullable column OK |

---

## E-02 — Commodity Registry

| Story ID | TDS / ADR | New requirements? | Dependencies | AC testable | DoD measurable | Notes |
|----------|-----------|-------------------|--------------|-------------|----------------|-------|
| E-02-S01 | TDS-006, TDS-009 §12.1 | No | E-01-S03 ✓ | Yes — role counts | Yes — cotton row | 6 roles, 2 active |
| E-02-S02 | TDS-006, TDS-012 §10, ADR-003 | No | E-01-S10, S01 ✓ | Yes — activation swap | Yes — audit event | |
| E-02-S03 | TDS-009 §4, §11 | No | S02 ✓ | Yes — validator tests | Yes — reject invalid | Embeds founder clarifications |
| E-02-S04 | TDS-009 §11.1 | No | S01–S03 ✓ | Yes — fixture snapshot | Yes — active v1.0.0 | Weights PROPOSED in TDS |
| E-02-S05 | TDS-010 §10, TDS-012 §4 | No | S04, E-00-S03, S07 ✓ | Yes — contract tests | Yes — OpenAPI | Public read only |
| E-02-S06 | TDS-010 §10.3, TDS-012 | No | S02, S05 ✓ | Yes — API key 401 | Yes — ops doc | Internal only |
| E-02-S07 | TDS-003, TDS-009 §12.3 | No | S04, S05 ✓ | Yes — service load | Yes — cache TTL | |

### E-02 Findings

| ID | Severity | Finding | Action |
|----|----------|---------|--------|
| E02-1 | Info | MSP 3% and partial 50% in S03/S04 — align with founder clarifications | Not new if already approved |
| E02-2 | Info | phase_1_active_roles farmer/trader only | Matches TDS-009 — ginner etc. inactive |

---

## Cross-Epic Dependency Validation

| Rule | Valid? |
|------|--------|
| E-01 does not require E-02 | ✓ |
| E-02 requires E-01-S03, S10 | ✓ |
| E-00-S08 before E-01-S05 | ✓ |
| No circular deps | ✓ |

---

## Stories That Must Not Be Started Early

| Story | Wait for |
|-------|----------|
| E-01-* | E-00 M0 minimum: S01, S02, S06 for S01; full E-00 for S04/S05 |
| E-02-* | E-01-S03, S10 |
| Any E-03+ | Not in audit scope — requires E-02-S04 |

---

## Conclusion

All **26 stories** in E-00–E-02 **PASS** audit for Sprint planning. No story introduces net-new product capabilities beyond frozen TDS/founder/ADR baseline. Implementation may proceed per TDS-014 sequencing.
