"""Time-series validation for forecast datasets — PI11 Track B."""

from backend.app.services.forecast.validation.rolling import (
    DEFAULT_PRIMARY_HORIZON_DAYS,
    RollingValidationResult,
    RollingValidationSpec,
    ValidationFold,
    assert_no_label_leakage,
    build_rolling_folds,
    dataset_rows_from_pi10_fixture,
    label_realization_date,
    render_time_series_validation_report,
    run_rolling_validation,
)

__all__ = [
    "DEFAULT_PRIMARY_HORIZON_DAYS",
    "RollingValidationResult",
    "RollingValidationSpec",
    "ValidationFold",
    "assert_no_label_leakage",
    "build_rolling_folds",
    "dataset_rows_from_pi10_fixture",
    "label_realization_date",
    "render_time_series_validation_report",
    "run_rolling_validation",
]
