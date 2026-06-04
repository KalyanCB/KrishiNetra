"""NCDEX public EOD bhavcopy UDiFF CSV parser — KAPAS Shankar contracts."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from backend.app.services.ingest.ncdex.constants import (
    DEFAULT_QUOTE_UNIT,
    FUTURES_SERIES,
    INR_PER_20KG_TO_QUINTAL,
    KAPAS_SYMBOLS,
)


class NcdexBhavParseError(ValueError):
    """Raised when UDiFF bhav content cannot be parsed."""


@dataclass(frozen=True, slots=True)
class NcdexKapasContractRow:
    """One parsed KAPAS futures contract row from UDiFF bhav."""

    as_of_date: date
    contract_symbol: str
    expiry_date: date
    settle_price: Decimal
    quote_unit: str
    settle_price_quintal: Decimal
    open_interest: int | None
    volume: Decimal | None
    series: str | None


# UDiFF column aliases (MDAC schema + legacy short headers).
_DATE_COLUMNS = ("TradDt", "BizDt", "RptDt", "Trade Date", "Business Date")
_SYMBOL_COLUMNS = ("TckrSymb", "Symbol", "SYMBOL", "Ticker")
_SERIES_COLUMNS = ("SctySrs", "Series", "SERIES", "Instrument Type")
_EXPIRY_COLUMNS = ("XpryDt", "Expiry Date", "EXPIRY_DT", "ExpiryDt")
_SETTLE_COLUMNS = (
    "SttlPric",
    "Settle Price",
    "SETTLE_PR",
    "Settlement Price",
    "Close Price",
    "ClsPric",
)
_OI_COLUMNS = ("OpnIntrst", "Open Interest", "OPEN_INT", "OI")
_VOLUME_COLUMNS = ("TtlTradgVol", "Total Traded Volume", "VOLUME", "Traded Volume")


def parse_udiff_bhav_csv(
    content: str | bytes,
    *,
    as_of_date: date | None = None,
) -> list[NcdexKapasContractRow]:
    """
    Parse NCDEX UDiFF bhav CSV and return KAPAS / SHANKRKPAS futures rows.

    Deterministic: rows sorted by (expiry_date, contract_symbol).
    """
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise NcdexBhavParseError("CSV missing header row")

    field_map = {name.strip(): name for name in reader.fieldnames if name}
    rows: list[NcdexKapasContractRow] = []
    errors: list[str] = []

    for index, raw in enumerate(reader):
        try:
            parsed = _parse_row(raw, field_map=field_map, default_as_of=as_of_date)
            if parsed is not None:
                rows.append(parsed)
        except NcdexBhavParseError as exc:
            errors.append(f"row[{index}]: {exc}")

    if not rows and errors:
        raise NcdexBhavParseError("; ".join(errors))

    return sorted(rows, key=lambda row: (row.expiry_date, row.contract_symbol))


def quintal_from_20kg(price_per_20kg: Decimal) -> Decimal:
    """Convert NCDEX KAPAS ₹/20 kg settle to ₹/quintal (×5)."""
    return (price_per_20kg * INR_PER_20KG_TO_QUINTAL).quantize(Decimal("0.0001"))


def default_observed_at(as_of_date: date) -> datetime:
    """EOD anchor for replay (NCDEX session close proxy)."""
    return datetime(
        as_of_date.year,
        as_of_date.month,
        as_of_date.day,
        17,
        30,
        tzinfo=UTC,
    )


def _parse_row(
    row: dict[str, str],
    *,
    field_map: dict[str, str],
    default_as_of: date | None,
) -> NcdexKapasContractRow | None:
    symbol = _optional_str(_first_value(row, field_map, _SYMBOL_COLUMNS))
    if symbol is None or symbol.upper() not in KAPAS_SYMBOLS:
        return None

    series = _optional_str(_first_value(row, field_map, _SERIES_COLUMNS))
    if series is not None and series.upper() not in FUTURES_SERIES:
        return None

    trade_raw = _first_value(row, field_map, _DATE_COLUMNS)
    trade_date = _parse_date(trade_raw) if trade_raw else default_as_of
    if trade_date is None:
        raise NcdexBhavParseError("missing trade date")

    expiry_raw = _first_value(row, field_map, _EXPIRY_COLUMNS)
    if expiry_raw is None:
        raise NcdexBhavParseError("missing expiry date")
    expiry_date = _parse_date(expiry_raw)

    settle_raw = _first_value(row, field_map, _SETTLE_COLUMNS)
    if settle_raw is None:
        raise NcdexBhavParseError("missing settlement price")
    settle_price = _parse_decimal(settle_raw)
    if settle_price <= 0:
        raise NcdexBhavParseError(f"invalid settle price {settle_raw!r}")

    oi_raw = _first_value(row, field_map, _OI_COLUMNS)
    open_interest: int | None = None
    if oi_raw is not None and oi_raw not in ("", "-", "0"):
        open_interest = _parse_int(oi_raw)

    vol_raw = _first_value(row, field_map, _VOLUME_COLUMNS)
    volume: Decimal | None = None
    if vol_raw is not None and vol_raw not in ("", "-"):
        volume = _parse_decimal(vol_raw)

    return NcdexKapasContractRow(
        as_of_date=trade_date,
        contract_symbol=symbol.upper(),
        expiry_date=expiry_date,
        settle_price=settle_price,
        quote_unit=DEFAULT_QUOTE_UNIT,
        settle_price_quintal=quintal_from_20kg(settle_price),
        open_interest=open_interest,
        volume=volume,
        series=series,
    )


def _first_value(
    row: dict[str, str],
    field_map: dict[str, str],
    candidates: tuple[str, ...],
) -> str | None:
    for candidate in candidates:
        key = field_map.get(candidate)
        if key is None:
            continue
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_date(raw: str) -> date:
    text = raw.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise NcdexBhavParseError(f"unrecognized date {raw!r}")


def _parse_decimal(raw: str) -> Decimal:
    cleaned = raw.strip().replace(",", "")
    if not cleaned or cleaned == "-":
        raise NcdexBhavParseError(f"invalid decimal {raw!r}")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise NcdexBhavParseError(f"invalid decimal {raw!r}") from exc


def _parse_int(raw: str) -> int | None:
    cleaned = raw.strip().replace(",", "")
    if not cleaned or cleaned == "-":
        return None
    try:
        return int(Decimal(cleaned))
    except (InvalidOperation, ValueError) as exc:
        raise NcdexBhavParseError(f"invalid integer {raw!r}") from exc
