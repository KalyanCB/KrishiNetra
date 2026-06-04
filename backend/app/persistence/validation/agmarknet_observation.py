"""Agmarknet price/arrival observation field validation (PI8 Track A)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    SOURCE_AGMARKNET,
)

MIN_COTTON_PRICE_INR = Decimal("100")
MAX_COTTON_PRICE_INR = Decimal("100000")
MIN_ARRIVAL_VOLUME = Decimal("0")
MAX_ARRIVAL_VOLUME = Decimal("500000")
MAX_OBSERVED_DATE_LAG_DAYS = 1


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Single failed validation check."""

    check: str
    message: str


@dataclass(frozen=True, slots=True)
class ObservationValidationOutcome:
    """Result of validating one observation row."""

    passed: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)


def validate_price_observation_fields(
    *,
    market_id: str | None,
    commodity_id: str | None,
    price_type: str | None,
    value: Decimal | None,
    unit: str | None,
    currency: str | None,
    observed_at: datetime | None,
    as_of_date: date | None,
    source: str | None,
    known_market_ids: frozenset[str],
    known_commodity_ids: frozenset[str],
) -> ObservationValidationOutcome:
    """Run null, range, mapping, and date checks on a price observation."""
    issues: list[ValidationIssue] = []

    if not market_id:
        issues.append(ValidationIssue("null_fields", "market_id is required"))
    if not commodity_id:
        issues.append(ValidationIssue("null_fields", "commodity_id is required"))
    if not price_type:
        issues.append(ValidationIssue("null_fields", "price_type is required"))
    if value is None:
        issues.append(ValidationIssue("null_fields", "value is required"))
    if not unit:
        issues.append(ValidationIssue("null_fields", "unit is required"))
    if not currency:
        issues.append(ValidationIssue("null_fields", "currency is required"))
    if observed_at is None:
        issues.append(ValidationIssue("null_fields", "observed_at is required"))
    if as_of_date is None:
        issues.append(ValidationIssue("null_fields", "as_of_date is required"))
    if not source:
        issues.append(ValidationIssue("null_fields", "source is required"))

    if (
        value is not None
        and (value < MIN_COTTON_PRICE_INR or value > MAX_COTTON_PRICE_INR)
    ):
        issues.append(
            ValidationIssue(
                "price_range",
                f"value must be in [{MIN_COTTON_PRICE_INR}, {MAX_COTTON_PRICE_INR}], "
                f"got {value}",
            )
        )

    if commodity_id and commodity_id not in known_commodity_ids:
        issues.append(
            ValidationIssue(
                "commodity_mapping",
                f"commodity_id {commodity_id!r} not in registry",
            )
        )
    elif commodity_id and commodity_id != COTTON_COMMODITY_ID:
        issues.append(
            ValidationIssue(
                "commodity_mapping",
                f"expected cotton commodity_id, got {commodity_id!r}",
            )
        )

    if market_id and market_id not in known_market_ids:
        issues.append(
            ValidationIssue(
                "market_mapping",
                f"market_id {market_id!r} not in registry",
            )
        )

    if source and source != SOURCE_AGMARKNET:
        issues.append(
            ValidationIssue(
                "source",
                f"expected source {SOURCE_AGMARKNET!r}, got {source!r}",
            )
        )

    if observed_at is not None and as_of_date is not None:
        lag = (observed_at.date() - as_of_date).days
        if lag < 0 or lag > MAX_OBSERVED_DATE_LAG_DAYS:
            issues.append(
                ValidationIssue(
                    "date_consistency",
                    f"observed_at date must be within {MAX_OBSERVED_DATE_LAG_DAYS} "
                    f"day(s) after as_of_date, lag={lag}",
                )
            )

    return ObservationValidationOutcome(
        passed=len(issues) == 0,
        issues=tuple(issues),
    )


def validate_arrival_observation_fields(
    *,
    market_id: str | None,
    commodity_id: str | None,
    volume: Decimal | None,
    unit: str | None,
    observed_at: datetime | None,
    as_of_date: date | None,
    source: str | None,
    known_market_ids: frozenset[str],
    known_commodity_ids: frozenset[str],
) -> ObservationValidationOutcome:
    """Run null, range, mapping, and date checks on an arrival observation."""
    issues: list[ValidationIssue] = []

    if not market_id:
        issues.append(ValidationIssue("null_fields", "market_id is required"))
    if not commodity_id:
        issues.append(ValidationIssue("null_fields", "commodity_id is required"))
    if volume is None:
        issues.append(ValidationIssue("null_fields", "volume is required"))
    if not unit:
        issues.append(ValidationIssue("null_fields", "unit is required"))
    if observed_at is None:
        issues.append(ValidationIssue("null_fields", "observed_at is required"))
    if as_of_date is None:
        issues.append(ValidationIssue("null_fields", "as_of_date is required"))
    if not source:
        issues.append(ValidationIssue("null_fields", "source is required"))

    if (
        volume is not None
        and (volume < MIN_ARRIVAL_VOLUME or volume > MAX_ARRIVAL_VOLUME)
    ):
        issues.append(
            ValidationIssue(
                "arrival_range",
                f"volume must be in [{MIN_ARRIVAL_VOLUME}, {MAX_ARRIVAL_VOLUME}], "
                f"got {volume}",
            )
        )

    if commodity_id and commodity_id not in known_commodity_ids:
        issues.append(
            ValidationIssue(
                "commodity_mapping",
                f"commodity_id {commodity_id!r} not in registry",
            )
        )
    elif commodity_id and commodity_id != COTTON_COMMODITY_ID:
        issues.append(
            ValidationIssue(
                "commodity_mapping",
                f"expected cotton commodity_id, got {commodity_id!r}",
            )
        )

    if market_id and market_id not in known_market_ids:
        issues.append(
            ValidationIssue(
                "market_mapping",
                f"market_id {market_id!r} not in registry",
            )
        )

    if source and source != SOURCE_AGMARKNET:
        issues.append(
            ValidationIssue(
                "source",
                f"expected source {SOURCE_AGMARKNET!r}, got {source!r}",
            )
        )

    if observed_at is not None and as_of_date is not None:
        lag = (observed_at.date() - as_of_date).days
        if lag < 0 or lag > MAX_OBSERVED_DATE_LAG_DAYS:
            issues.append(
                ValidationIssue(
                    "date_consistency",
                    f"observed_at date must be within {MAX_OBSERVED_DATE_LAG_DAYS} "
                    f"day(s) after as_of_date, lag={lag}",
                )
            )

    return ObservationValidationOutcome(
        passed=len(issues) == 0,
        issues=tuple(issues),
    )
