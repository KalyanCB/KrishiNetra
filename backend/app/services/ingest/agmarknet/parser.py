"""Parse OGD Agmarknet JSON envelopes and row records (spike only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


class AgmarknetParseError(ValueError):
    """Raised when an OGD row or envelope cannot be parsed."""


@dataclass(frozen=True, slots=True)
class AgmarknetRecord:
    """Normalized OGD mandi row (prices + optional arrival volume)."""

    state: str
    district: str
    market: str
    commodity: str
    variety: str | None
    grade: str | None
    arrival_date: date
    min_price: Decimal | None
    max_price: Decimal | None
    modal_price: Decimal | None
    arrival_tonnes: Decimal | None


def parse_ogd_response(payload: dict[str, Any]) -> list[AgmarknetRecord]:
    """Extract and parse all rows from an OGD Data API JSON body."""
    records = payload.get("records")
    if records is None:
        msg = "OGD payload missing 'records' array"
        raise AgmarknetParseError(msg)
    if not isinstance(records, list):
        msg = f"'records' must be a list, got {type(records).__name__}"
        raise AgmarknetParseError(msg)

    parsed: list[AgmarknetRecord] = []
    errors: list[str] = []
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            errors.append(f"records[{index}]: expected object")
            continue
        try:
            parsed.append(parse_record(row))
        except AgmarknetParseError as exc:
            errors.append(f"records[{index}]: {exc}")

    if errors and not parsed:
        raise AgmarknetParseError("; ".join(errors))
    return parsed


def parse_record(row: dict[str, Any]) -> AgmarknetRecord:
    """Parse a single OGD mandi record dict."""
    state = _require_str(row, "state")
    district = _require_str(row, "district")
    market = _require_str(row, "market")
    commodity = _require_str(row, "commodity")
    arrival_raw = _require_str(row, "arrival_date")

    return AgmarknetRecord(
        state=state,
        district=district,
        market=market,
        commodity=commodity,
        variety=_optional_str(row.get("variety")),
        grade=_optional_str(row.get("grade")),
        arrival_date=parse_arrival_date(arrival_raw),
        min_price=_optional_decimal(row.get("min_price")),
        max_price=_optional_decimal(row.get("max_price")),
        modal_price=_optional_decimal(row.get("modal_price")),
        arrival_tonnes=_optional_arrival_tonnes(row),
    )


def parse_arrival_date(raw: str) -> date:
    """Parse OGD `arrival_date` in DD/MM/YYYY format."""
    parts = raw.strip().split("/")
    if len(parts) != 3:
        msg = f"arrival_date must be DD/MM/YYYY, got {raw!r}"
        raise AgmarknetParseError(msg)
    try:
        day, month, year = (int(parts[0]), int(parts[1]), int(parts[2]))
        return date(year, month, day)
    except ValueError as exc:
        msg = f"invalid arrival_date {raw!r}"
        raise AgmarknetParseError(msg) from exc


def _require_str(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        msg = f"missing required field {key!r}"
        raise AgmarknetParseError(msg)
    return str(value).strip()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        msg = f"invalid numeric value {value!r}"
        raise AgmarknetParseError(msg) from exc


def _optional_arrival_tonnes(row: dict[str, Any]) -> Decimal | None:
    """Portal/CSV rows may use arrival_tonnes or arrival (tonnes)."""
    for key in ("arrival_tonnes", "arrival"):
        if key in row and row[key] is not None and row[key] != "":
            return _optional_decimal(row[key])
    return None
