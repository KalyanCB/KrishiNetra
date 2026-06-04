# Phase 1 Source Decisions — Cotton Intelligence

**Date:** 2026-06-04  
**Epic:** E-01 Phase 4 (research)  
**Status:** Decision record for E-02/E-03 planning  
**Inputs:** [COTTON_DATA_SOURCE_VALIDATION.md](./COTTON_DATA_SOURCE_VALIDATION.md), [AGMARKNET_INGESTION_SPIKE.md](./AGMARKNET_INGESTION_SPIKE.md), [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md)

---

## 1. Decision Legend

| Status | Meaning |
|--------|---------|
| **APPROVED** | Use in Phase 1 production path |
| **CONDITIONAL** | Use with documented constraints / founder sign-off |
| **DEFERRED** | Not Phase 1 primary path |

---

## 2. Source Decision Table

| Source | Status | Confidence | Cost | Licensing | Complexity | Phase 1 role |
|--------|--------|------------|------|-----------|------------|--------------|
| **Agmarknet (OGD)** | **APPROVED** | Medium | Free (API key) | NDSAP open data | Medium — mapping + lag handling | Primary Market observations |
| **IMD** | **CONDITIONAL** | Medium | Free API; DSP paid for deep history | Govt terms; IP whitelist | High — ops whitelist | Weather agent observations |
| **NASA POWER** | **APPROVED** | High | Free | Open NASA terms | Low — grid API | Weather backfill / gap-fill |
| **USDA FAS** | **APPROVED** | High | Free | Open data attribution | Low | Global/Demand agent |
| **CCI** | **CONDITIONAL** | Medium | Free (public notices) | Confirm scrape ToS | Medium — manual/events | Policy signal components |
| **PIB** | **APPROVED** | High | Free | Govt press | Low — RSS/HTML | Policy announcements |
| **NCDEX KAPAS** | **CONDITIONAL** | Medium | **Commercial** (DS-001) | Exchange sublicense | High — vendor contract | Futures agent (required) |

---

## 3. Per-Source Rationale

### Agmarknet — APPROVED

- Mandi price + arrival coverage for cotton belts.
- OGD API + zip backfill path validated in spike.
- Risks: lag (DC-001), commodity string normalization — mitigated via quality snapshot.

### IMD — CONDITIONAL

- Required for operational India rainfall; blocked on IP whitelist and DSP for 10y backfill.
- Fallback: NASA POWER for historical grid features.

### NASA POWER — APPROVED

- Stable programmatic API; no whitelist.
- Used for weather feature backfill where IMD gaps exist.

### USDA — APPROVED

- FAS Open Data / PSD for global cotton balance; low row count.
- Maps to Global/Demand `signal_components`.

### CCI — CONDITIONAL

- Policy signal needs `cci_active_procurement`; no API.
- Phase 1: PIB + manual procurement calendar seed until automated watcher.

### PIB — APPROVED

- Official MSP/procurement announcements; event-driven Policy signal updates.

### NCDEX — CONDITIONAL

- Cotton registry **requires** Futures agent (TDS-009).
- Blocked on **DS-001 founder decision** and commercial license — not REQ-070 public source.

---

## 4. Deferred / Secondary (Not in table above)

| Source | Status | Notes |
|--------|--------|-------|
| eNAM | DEFERRED | No public API; secondary confirmatory only |
| ICAC | CONDITIONAL | Commercial embed needs Secretariat approval |
| MCX | DEFERRED | DS-001 evaluates vs NCDEX |

---

## 5. Phase 1 Minimum Viable Source Set

**Must have:** Agmarknet (OGD), NASA POWER, USDA, PIB, licensed NCDEX (or approved DS-001 vendor).

**Should have:** IMD operational rainfall, CCI event feed.

**Nice to have:** eNAM cross-check, ICAC monthly series.

---

*End of Phase 1 source decisions.*
