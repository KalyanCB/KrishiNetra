# E-00-S07 Report — Structured Logging and trace_id

**Story:** E-00-S07 | **Status:** Done | **Date:** 2026-06-03

## Acceptance criteria evidence

| AC | Evidence |
|----|----------|
| AC-1 | `TraceIdMiddleware` accepts/generates `X-Trace-Id` |
| AC-2 | `JsonLogFormatter` fields: `timestamp`, `level`, `trace_id`, `message`, `module` |
| AC-3 | Response echoes `X-Trace-Id` header |
| AC-4 | Default fields are operational only (no user PII) |
| AC-5 | `LOG_LEVEL` env via `configure_logging()` |

## Implementation

- `backend/app/middleware/trace_id.py` — middleware
- `backend/app/logging_config.py` — JSON structured logging
- `backend/app/main.py` — wires logging + middleware
- `backend/app/events/correlation.py` — documents `trace_id` ↔ `EventType` correlation (TDS-005 prep)

## Event correlation strategy (TDS-005)

HTTP requests receive a `trace_id` (UUID or client-supplied). Future business events (`EventType` from `shared.domain`) will include the same `trace_id` in structured logs and event payloads for idempotent processing keys `(event_type, commodity_id, as_of_date, entity_id)` plus trace lineage. E-09 audit extends this identifier without changing middleware.

## Test results

```
uv run pytest tests/unit/test_trace_id.py -v  → 3 passed
```

Sample log context: `extra={"trace_id": "<uuid>"}` on request start/complete.

## ADR / TDS compliance

- TDS-013 §5.1 structured JSON logs
- TDS-010 §14 trace header propagation
- TDS-012 §6 prep only (no audit table in E-00)

## Risks

- Full event bus and audit persistence deferred to later epics
