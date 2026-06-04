# Signal Quality Report — PI9 Track E

**Date:** 2026-06-04  
**PI:** PI9 Track E (KDO — `SignalQualityService`)  
**Status:** Signal quality assessment from `structured_signal` + `signal_snapshot`  
**Prerequisites:** Market + Weather generators (Tracks A/B); signal persistence (Track C)

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Signal quality service operational? | **Yes** — aggregates from `structured_signal` + `signal_snapshot` |
| Commodity / `as_of_date` | `cotton` / `2026-06-04` |
| `signal_count` (structured rows) | **2** (Market + Weather, PI9 enhanced degraded) |
| Snapshot present? | **Yes** |
| Coverage ratio (all registry agents) | **0.5000** |
| Required coverage ratio | **0.5000** (Market present; Futures missing per DS-001) |
| Signal freshness | **`fresh`** |
| Mean agent confidence | **0.6150** |

**Overall:** **PASS** — PI9 Track E deliverable tracks signal_count, coverage, freshness, and confidence aggregates without forecast/decision/LLM scope.

---

## 2. Coverage

| Metric | Value |
|--------|-------|
| Agents present / expected | **2** / **4** |
| Required present / expected | **1** / **2** |
| `signals_missing` (required) | `['Futures']` |
| Optional agents missing | `['Policy']` |
| Agents present | `['Market', 'Weather']` |

Coverage uses active `commodity_registry.required_agents[]` + `optional_agents[]` as the denominator. `signals_missing` lists required agents with no `structured_signal` row for the day.

---

## 3. Freshness

| Metric | Value |
|--------|-------|
| Latest `as_of_timestamp` | `2026-06-04 12:00:00+00:00` |
| `signal_lag_hours` | **2.0** |
| Freshness classification | **`fresh`** |

Freshness derives from the latest `structured_signal.as_of_timestamp` vs assessment clock, using the same 48-hour stale threshold as observation quality (TDS-006 §3.17).

---

## 4. Confidence aggregates

| Metric | Value |
|--------|-------|
| Count | **2** |
| Min | **0.55** |
| Max | **0.68** |
| Mean | **0.6150** |

Per-agent map:

| Agent | Confidence |
|-------|------------|
| Market | 0.68 |
| Weather | 0.55 |

---

## 5. Snapshot alignment

| Metric | Value |
|--------|-------|
| `snapshot_signal_count` | **2** |
| Snapshot aligned with structured rows? | **True** |
| `snapshot_hash` | SHA-256 over canonical PI9 payload |

When `signal_snapshot` exists, `snapshot_signal_count` is compared to `structured_signal` row count for the same `(commodity_id, as_of_date, registry_id)`.

---

## 6. Tests

| Module | Unit (no DB) | Integration (`DATABASE_URL`) | Total |
|--------|--------------|------------------------------|-------|
| `test_signal_quality.py` | 10 | 1 | **11** |

```bash
uv run pytest tests/unit/test_signal_quality.py -q
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run pytest tests/unit/test_signal_quality.py -q
```

---

## 7. Deliverables

| Artifact | Path |
|----------|------|
| Signal quality service | `backend/app/services/signals/quality/service.py` |
| Metrics helpers | `backend/app/services/signals/quality/metrics.py` |
| Test fixtures | `tests/fixtures/signal_quality.py` |
| Unit tests | `tests/unit/test_signal_quality.py` |
| Report | `docs/reviews/SIGNAL_QUALITY_REPORT.md` |

---

## 8. Sample metrics payload

```json
{
  "signal_count": 2,
  "snapshot_signal_count": 2,
  "snapshot_present": true,
  "snapshot_aligned": true,
  "coverage_ratio": 0.5,
  "required_coverage_ratio": 0.5,
  "signals_missing": ["Futures"],
  "optional_agents_missing": ["Policy"],
  "agents_present": ["Market", "Weather"],
  "signal_lag_hours": 2.0,
  "freshness": "fresh",
  "confidence": {
    "count": 2,
    "min": 0.55,
    "max": 0.68,
    "mean": 0.615,
    "by_agent": {
      "Market": "0.6800",
      "Weather": "0.5500"
    }
  }
}
```

---

## 9. Reference return values (PI9 Track E)

| Item | Value |
|------|-------|
| Service path | `backend/app/services/signals/quality/service.py` |
| PI9 unit test count | **10** (+ 1 integration with `DATABASE_URL`) |
| Report path | `docs/reviews/SIGNAL_QUALITY_REPORT.md` |

---

*End of signal quality report — PI9 Track E.*
