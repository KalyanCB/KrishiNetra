"""Rolling time-ordered train/test folds for forecast baseline evaluation (PI11 Track B hook)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FoldPredictFn = Callable[
    [NDArray[np.int64], NDArray[np.int64]],
    NDArray[np.float64],
]

DEFAULT_MIN_TRAIN_SIZE = 60
DEFAULT_TEST_SIZE = 20
DEFAULT_STEP = 20


@dataclass(frozen=True, slots=True)
class RollingFold:
    """One expanding-window fold: train prefix, contiguous test block."""

    fold_index: int
    train_indices: NDArray[np.int64]
    test_indices: NDArray[np.int64]


def iter_rolling_folds(
    n_samples: int,
    *,
    min_train_size: int = DEFAULT_MIN_TRAIN_SIZE,
    test_size: int = DEFAULT_TEST_SIZE,
    step: int | None = None,
) -> Iterator[RollingFold]:
    """
    Expanding-window folds ordered by time (indices 0..n-1).

    Yields while ``train_end + test_size <= n_samples``. If the corpus is too
    short for multiple steps, yields a single fold with train ``[0, min_train)``
    and test ``[min_train, n)`` when ``min_train + test_size > n`` but ``n > min_train``.
    """
    if n_samples < 2:
        return
    stride = step if step is not None else test_size
    if n_samples < min_train_size + test_size:
        train_end = min(min_train_size, n_samples - 1)
        if train_end < 1:
            return
        test_end = n_samples
        yield RollingFold(
            fold_index=0,
            train_indices=np.arange(0, train_end, dtype=np.int64),
            test_indices=np.arange(train_end, test_end, dtype=np.int64),
        )
        return

    fold_idx = 0
    train_end = min_train_size
    while train_end + test_size <= n_samples:
        yield RollingFold(
            fold_index=fold_idx,
            train_indices=np.arange(0, train_end, dtype=np.int64),
            test_indices=np.arange(train_end, train_end + test_size, dtype=np.int64),
        )
        fold_idx += 1
        train_end += stride


def collect_out_of_sample_predictions(
    y: NDArray[np.float64],
    *,
    min_train_size: int = DEFAULT_MIN_TRAIN_SIZE,
    test_size: int = DEFAULT_TEST_SIZE,
    step: int | None = None,
    fit_predict_fold: FoldPredictFn,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """
    Pool held-out predictions across all rolling folds.

    ``fit_predict_fold(train_idx, test_idx) -> y_pred`` must return predictions
    aligned with ``test_idx``.
    """
    y_true_parts: list[NDArray[np.float64]] = []
    y_pred_parts: list[NDArray[np.float64]] = []
    for fold in iter_rolling_folds(
        y.shape[0],
        min_train_size=min_train_size,
        test_size=test_size,
        step=step,
    ):
        y_pred = fit_predict_fold(fold.train_indices, fold.test_indices)
        y_true_parts.append(y[fold.test_indices])
        y_pred_parts.append(np.asarray(y_pred, dtype=np.float64))
    if not y_true_parts:
        msg = "rolling evaluation produced no out-of-sample predictions"
        raise ValueError(msg)
    return np.concatenate(y_true_parts), np.concatenate(y_pred_parts)
