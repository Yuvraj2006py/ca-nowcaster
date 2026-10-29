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


def to_2d_float(X: Any, *, name: str = "X") -> np.ndarray:
    """Coerce a feature matrix to a 2-d float64 numpy array.

    Inputs: X as DataFrame, ndarray, or nested sequence.
    Outputs: shape (n, p) float64 array (NaNs preserved for imputers / DFM).
    Time allowed to know: values present in X only (caller enforces as_of).
    """
    if X is None:
        raise ValueError(f"{name} must not be None")
    if hasattr(X, "to_numpy"):
        arr = np.asarray(X.to_numpy(), dtype=np.float64)
    else:
        arr = np.asarray(X, dtype=np.float64)

    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 2-d, got shape {arr.shape}")
    return arr


def require_feature_matrix(X: Any, *, name: str = "X", min_cols: int = 1) -> np.ndarray:
    """Validate that X has at least ``min_cols`` feature columns.

    Inputs: feature matrix; minimum column count (Phase 3 candidates need >= 1).
    Outputs: 2-d float64 array.
    Time allowed to know: structure of X only beyond values passed in.
    """
    arr = to_2d_float(X, name=name)
    if arr.shape[1] < min_cols:
        raise ValueError(
            f"{name} needs at least {min_cols} feature column(s), got {arr.shape[1]}"
        )
    return arr


def column_names(X: Any, n_cols: int) -> list[str]:
    """Return column names for X, or synthetic names when absent.

    Inputs: feature matrix; column count.
    Outputs: list of length n_cols.
    Time allowed to know: column labels only.
    """
    if hasattr(X, "columns"):
        return [str(c) for c in list(X.columns)[:n_cols]]
    return [f"f{i}" for i in range(n_cols)]


def median_impute_fit(X: np.ndarray) -> np.ndarray:
    """Compute per-column medians on training X (NaN-safe).

    Inputs: training feature matrix (n, p), may contain NaNs.
    Outputs: shape (p,) medians; 0.0 where a column is entirely missing.
    Time allowed to know: training X only.
    """
    medians = np.nanmedian(X, axis=0)
    medians = np.asarray(medians, dtype=np.float64)
    medians[~np.isfinite(medians)] = 0.0
    return medians


def median_impute_apply(X: np.ndarray, medians: np.ndarray) -> np.ndarray:
    """Replace NaNs / non-finite values with training column medians.

    Inputs: feature matrix; medians from median_impute_fit.
    Outputs: copy of X with finite floats only.
    Time allowed to know: medians estimated on the fit window only.
    """
    out = np.array(X, dtype=np.float64, copy=True)
    if out.shape[1] != medians.shape[0]:
        raise ValueError(
            f"feature width {out.shape[1]} != median width {medians.shape[0]}"
        )
    for j in range(out.shape[1]):
        mask = ~np.isfinite(out[:, j])
        if mask.any():
            out[mask, j] = medians[j]
    return out


def align_xy(X: Any, y: Any) -> tuple[np.ndarray, np.ndarray]:
    """Coerce and length-check X and y for supervised candidates.

    Inputs: feature matrix X; target vector y.
    Outputs: (X_2d, y_1d) with matching row counts.
    Time allowed to know: rows passed into fit/predict only.
    """
    X_arr = require_feature_matrix(X)
    y_arr = to_1d_float(y, name="y")
    if X_arr.shape[0] != y_arr.shape[0]:
        raise ValueError(
            f"X and y length mismatch: X has {X_arr.shape[0]} rows, y has {y_arr.shape[0]}"
        )
    return X_arr, y_arr
