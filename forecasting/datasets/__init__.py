"""PI10 Track D — supervised forecast target datasets (export/validation only)."""

from forecasting.datasets.builder import (
    FORECAST_HORIZONS,
    BuildResult,
    ForecastDatasetBuilder,
    HorizonDatasetStats,
    build_fixture_datasets,
    render_forecast_dataset_report,
)

__all__ = [
    "FORECAST_HORIZONS",
    "BuildResult",
    "ForecastDatasetBuilder",
    "ForecastTrainingDataset",
    "HorizonDatasetStats",
    "build_fixture_datasets",
    "load_fixture_training_dataset",
    "render_forecast_dataset_report",
]


def __getattr__(name: str) -> object:
    if name == "ForecastTrainingDataset":
        from forecasting.datasets.training import ForecastTrainingDataset

        return ForecastTrainingDataset
    if name == "load_fixture_training_dataset":
        from forecasting.datasets.training import load_fixture_training_dataset

        return load_fixture_training_dataset
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
