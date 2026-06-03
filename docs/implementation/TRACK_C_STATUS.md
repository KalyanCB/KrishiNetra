# Track C — Cotton Data Source Validation

**Program:** KrishiNetra KDO Parallel Execution  
**Track owner:** Track C worker  
**Branch (target):** `feature/cotton-data-research` — **not created** (git remote pending)  
**Last updated:** 2026-06-03

---

## Objective

Validate Phase 1 cotton ingestion sources (**Agmarknet, eNAM, IMD, NCDEX, USDA, ICAC**) for availability, access, refresh cadence, historical depth, licensing, and confidence; map each to domain agents (**Market, Weather, Policy, Demand, Futures, Global** with Global at `agents/global_signals/` per ADR-005). **No code.** Product context from frozen `docs/founder/` and TDS only.

---

## Status

| Field | Value |
|-------|-------|
| **Phase** | Research validation complete |
| **Deliverable** | [`docs/research/COTTON_DATA_SOURCE_VALIDATION.md`](../research/COTTON_DATA_SOURCE_VALIDATION.md) |
| **Epic consumer** | E-03 Ingestion & Observations (REQ-070 public; REQ-071 commercial futures) |
| **Out of scope** | Policy Agent (Agriculture Ministry MSP/CCI) — E-03 F-03-03 |

---

## Current Status

**Complete** — six sources validated; agent mapping and E-03 risk register documented.

---

## Completed Work

- [x] Per-source assessment: availability, access method, refresh frequency, historical depth, licensing, confidence (§3)
- [x] Agent mapping table (Market, Weather, Demand, Futures, Global/`global_signals`) per TDS-004, TDS-007, ADR-005
- [x] Cross-source ingest priority matrix and founder assumption verdicts (DA-001, DA-002, DA-003, DA-008)
- [x] E-03 non-code implications (registry strings, DataQualitySnapshot, basis pipeline, DS-001)
- [x] Web verification of OGD Agmarknet API, USDA FAS Open Data/PSD SOAP, ICAC registration/licensing (2026-06-03)
- [x] PROGRAM_STATUS.md Track C section updated

---

## In Progress

_None — Track C charter complete._

---

## Open Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| DS-001 | No commercial futures vendor (REQ-071) | High | NCDEX/MCX via authorized data vendor; blocks Futures Agent + DVA |
| — | Agmarknet lag/gaps (DC-001, FD-030) | Medium | OGD ingest + `agmarknet_lag_hours`; basis adjustment |
| — | eNAM no public API | Medium | P2 secondary; snapshot or SFAC data request |
| — | IMD DSP licensing / API whitelist | Medium | Operational API for daily; DSP for deep backtest |
| — | ICAC commercial redistribution | Medium | Secretariat written approval before product embed |

---

## Blockers

| Blocker | Status |
|---------|--------|
| Prior deliverable gap | **Resolved** — `COTTON_DATA_SOURCE_VALIDATION.md` delivered |
| Git branch `feature/cotton-data-research` | **Expected** — create when repo remote available |
| REQ-071 futures contract (DS-001) | **Program-level** — not Track C research scope; blocks E-03 production ingest |

---

## Next Actions

1. Founder/program: select REQ-071 futures data vendor (NCDEX vs MCX vs aggregator).
2. E-03: lock Agmarknet programmatic path to **data.gov.in Catalog API** (API key registration).
3. E-03: legal review for ICAC/USDA redistribution in SaaS MI outputs.
4. E-02-S04: keep registry source name strings unchanged (Agmarknet, eNAM, IMD, USDA, ICAC).

---

## Traceability

| Artifact | Link |
|----------|------|
| Cotton validation | [COTTON_DATA_SOURCE_VALIDATION.md](../research/COTTON_DATA_SOURCE_VALIDATION.md) |
| Data domains | [DATA_DOMAINS.md](../founder/DATA_DOMAINS.md) (read-only) |
| Forecast sources | [TDS-007 §3](../tds/TDS-007-Forecast-Architecture.md) |
| Agent architecture | [TDS-004](../tds/TDS-004-Agent-Architecture.md) |
| Global package | [ADR-005](../adrs/ADR-005-agent-package-naming.md) |
| Epic mapping | [TDS-014](../tds/TDS-014-Epic-Mapping.md) § E-03 |
| Readiness | [IMPLEMENTATION_READINESS_REVIEW.md](../reviews/IMPLEMENTATION_READINESS_REVIEW.md) §9 |

---

## Deliverables Produced

| Deliverable | Path |
|-------------|------|
| Cotton data source validation | `docs/research/COTTON_DATA_SOURCE_VALIDATION.md` |
| Track C status (this file) | `docs/implementation/TRACK_C_STATUS.md` |
| Program status (Track C section) | `docs/implementation/PROGRAM_STATUS.md` |
