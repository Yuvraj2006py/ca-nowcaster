"""Array / frame utilities for model fit and predict.

Inputs: feature matrices and target vectors from the evaluation harness or fixtures.
Outputs: plain numpy arrays and row counts.
Time allowed to know: only rows passed into fit/predict (caller enforces as_of).
"""

from __future__ import annotations

from typing import Any

import numpy as np


def to_1d_float(y: Any, *, name: str = "y") -> np.ndarray:
    """Coerce a target-like object to a 1-d float64 numpy array.

    Inputs: y as Series, ndarray, list, or DataFrame with one column.
    Outputs: shape (n,) float64 array (NaNs preserved; caller may reject them).
    Time allowed to know: values present in y only.
    """
    if hasattr(y, "to_numpy"):
        arr = np.asarray(y.to_numpy(), dtype=np.float64)
    else:
        arr = np.asarray(y, dtype=np.float64)

    if arr.ndim == 2 and arr.shape[1] == 1:
        arr = arr[:, 0]
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1-d (or single-column), got shape {arr.shape}")
    return arr


def n_rows(X: Any) -> int:
    """Return the number of prediction rows implied by X.

    Inputs: feature matrix (DataFrame, ndarray, or sequence).
    Outputs: row count (>= 0).
    Time allowed to know: structure of X only; feature values unused by baselines.
    """
    if X is None:
        raise ValueError("X must not be None")
    if hasattr(X, "shape"):
        shape = X.shape
        if len(shape) == 0:
            raise ValueError("X has scalar shape; expected at least 1-d")
        return int(shape[0])
    return len(X)


def require_finite_1d(y: np.ndarray, *, name: str = "y", min_len: int = 1) -> np.ndarray:
    """Validate a 1-d float array for baseline fitting.

    Inputs: candidate target array; minimum length.
    Outputs: the same array if valid.
    Time allowed to know: training y only.
    """
    if y.size < min_len:
        raise ValueError(f"{name} needs at least {min_len} observation(s), got {y.size}")
    if not np.isfinite(y).all():
        raise ValueError(f"{name} contains non-finite values")
    return y


def residual_std(residuals: np.ndarray) -> float:
    """Sample standard deviation of one-step residuals (ddof=1).

    Inputs: residual vector from the training window.
    Outputs: non-negative float; 0.0 when fewer than two residuals.
    Time allowed to know: training residuals only.
    """
    if residuals.size < 2:
        return 0.0
    return float(np.std(residuals, ddof=1))
