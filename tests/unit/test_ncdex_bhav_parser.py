"""E-04 F-04-05: NCDEX UDiFF bhav parser unit tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.services.ingest.ncdex.parser import (
    NcdexBhavParseError,
    parse_udiff_bhav_csv,
    quintal_from_20kg,
)

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "ncdex" / "udiff_kapas_sample.csv"


def test_parse_udiff_bhav_filters_kapas_only() -> None:
    content = FIXTURE_PATH.read_text(encoding="utf-8")
    rows = parse_udiff_bhav_csv(content)
    assert len(rows) == 4
    symbols = {row.contract_symbol for row in rows}
    assert symbols == {"KAPAS", "SHANKRKPAS"}


def test_parse_udiff_bhav_deterministic_order() -> None:
    content = FIXTURE_PATH.read_text(encoding="utf-8")
    first = parse_udiff_bhav_csv(content)
    second = parse_udiff_bhav_csv(content)
    assert [(r.expiry_date, r.contract_symbol) for r in first] == [
        (r.expiry_date, r.contract_symbol) for r in second
    ]


def test_quintal_conversion() -> None:
    assert quintal_from_20kg(Decimal("1345.50")) == Decimal("6727.5000")


def test_parse_row_missing_settle_raises() -> None:
    csv_text = "TradDt,TckrSymb,SctySrs,XpryDt\n2026-02-15,KAPAS,FUT,2026-02-28\n"
    with pytest.raises(NcdexBhavParseError):
        parse_udiff_bhav_csv(csv_text, as_of_date=date(2026, 2, 15))


def test_parse_fixture_near_far_values() -> None:
    content = FIXTURE_PATH.read_text(encoding="utf-8")
    rows = parse_udiff_bhav_csv(content)
    feb = next(row for row in rows if row.expiry_date == date(2026, 2, 28))
    assert feb.settle_price == Decimal("1345.50")
    assert feb.open_interest == 42
