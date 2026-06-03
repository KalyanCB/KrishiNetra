# Technical Debt Register — PI1

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Owner** | KDO / engineering |
| **Next review** | Post E-01-S10 or E-02-S04 |

---

## Severity legend

| Level | Meaning |
|-------|---------|
| **Critical** | Blocks next epic or production path |
| **High** | Should fix before dependent stories merge |
| **Medium** | Fix in same epic or next sprint |
| **Low** | Cosmetic or deferrable |

---

## Register

| ID | Item | Severity | Origin | Remediation | Owner epic |
|----|------|----------|--------|-------------|------------|
| TD-001 | `commodity_registry` table missing (E-01-S10) | **Critical** | E-01 gap | Implement `0003_commodity_registry` | E-01 |
| TD-002 | E-01-S04–S11 DDL not started | **Critical** | Epic incomplete | Execute per `E01_EXECUTION_PLAN.md` | E-01 |
| TD-003 | DS-001 / REQ-071 futures contract unsigned | **Critical** | Founder/commercial | RFP + NDU; see DS-001 | Program |
| TD-004 | Integration tests skip without `DATABASE_URL` | **High** | Dev ergonomics | Document `.env`; fix local PG port/auth conflicts | E-00 |
| TD-005 | `SeedRunner.apply` not implemented | **High** | E-01 stub | E-02-S01/S04 cotton seed | E-02 |
| TD-006 | Immutability proven on stub ORM only | **Medium** | S02 ahead of S06 | `test_forecast_version_immutable` on real table | E-01-S06 |
| TD-007 | Only `CommodityRepository`; no region/market repos | **Medium** | Minimal S03 | Add as E-02/E-03 need queries | E-02 |
| TD-008 | Redis MI client absent (E-01-S09) | **High** | S09 not started | Implement after S06 conceptual shape | E-01 |
| TD-009 | `data_quality_snapshot` absent (E-01-S08) | **High** | S08 not started | Migration before ingest | E-01 |
| TD-010 | v1 API routers return 501 stubs | **Low** | E-00 | Implement per epic (E-02-S05 first registry) | E-02 |
| TD-011 | Starlette/httpx deprecation warning in tests | **Low** | Dependency | Migrate to httpx2 when stable | E-00 |
| TD-012 | AST import checker misses dynamic imports | **Low** | E-00-S05 note | Accept M0; revisit if needed | E-00 |
| TD-013 | Monthly partition ops manual per ADR-002 | **Medium** | S04+ design | Ops runbook + calendar migrations | E-01-S04 |
| TD-014 | eNAM / ICAC production automation unclear | **High** | Track C | Contract/API before E-03 prod | E-03 |
| TD-015 | Agmarknet OGD API key not provisioned | **Medium** | E-03 prep | Register `api.data.gov.in` | E-03 |
| TD-016 | IMD API IP whitelist not applied | **Medium** | E-03 prep | Ops ticket to IMD | E-03 |
| TD-017 | E-01-S11 integration gate (80% persistence coverage) | **High** | Not started | After S04–S10 | E-01 |
| TD-018 | Single commit `30583fc` bundles E-00+E-01 | **Low** | Git history | Prefer story-scoped commits going forward | Process |
| TD-019 | `agents/explainability` path in manifest vs ADR-005 `global_signals` | **Low** | Layout drift | Align manifest in future E-00 touch | E-00 |
| TD-020 | Founder OQ-004 stability_token schema undefined | **Medium** | Open question | Before E-01-S07 recommendation_version | E-01 |

---

## Deferred work (explicit, not debt)

| Item | Reason |
|------|--------|
| InventoryPosition | Phase 2 / E-12 |
| Forecast / decision / agent runtime | Forbidden until respective epics |
| Production Terraform | Wave 4+ per infra README |
| Automated 7-year partition prune | Ops future |

---

## Summary by severity

| Severity | Count |
|----------|-------|
| Critical | 3 |
| High | 7 |
| Medium | 6 |
| Low | 4 |

**Top 3 actions:** TD-001 (S10), TD-002 (S04+ chain), TD-003 (DS-001 contract).
