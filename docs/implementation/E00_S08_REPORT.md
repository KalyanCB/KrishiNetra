# E-00-S08 Report — Shared Package Stubs

**Story:** E-00-S08 | **Status:** Done | **Date:** 2026-06-03

## Acceptance criteria evidence

| AC | Evidence |
|----|----------|
| AC-1 | `shared/domain/enums.py`: `AgentType`, `ActionType`, `PersonaType`, `LiquidityNeed`, `MarketRegime`, plus `CommodityType`, `EventType`, `Direction` |
| AC-2 | `shared/signal_contract/models.py`: `StructuredSignal` with value, direction, magnitude, confidence, as_of_timestamp |
| AC-3 | `shared/contracts/` placeholder documented |
| AC-4 | `uv run mypy` strict on `shared/` — pass |
| AC-5 | `shared_no_upward` CI rule; no upward imports in package |

## AgentType (TDS-004 / ADR-005)

| Member | Value |
|--------|-------|
| MARKET | Market |
| WEATHER | Weather |
| POLICY | Policy |
| DEMAND | Demand |
| FUTURES | Futures |
| GLOBAL | Global |

Global Agent code path remains `agents/global_signals/` per ADR-005; enum value `Global` per TDS-004.

## Test results

```
uv run pytest tests/unit/test_shared_contracts.py tests/unit/test_import_shared.py -v
  → 6 passed
uv run mypy  → pass
```

## ADR / TDS compliance

- TDS-004 §3 signal contract fields (snake_case attributes)
- TDS-006 attribute naming alignment
- TDS-005 `EventType` catalog stubbed for downstream events
- REQ-060 / REQ-090 traceability
- No InventoryPosition (Phase 2)

## Risks

- `shared/contracts` DTOs empty until E-09
