"""Ragged-edge fill strategies for monthly panels at a fixed as_of date.

After as_of filtering, series end at different months. These helpers only
impute trailing gaps after each series' last observed value within the panel
index — they never invent observations before the first print or fill interior
gaps (those stay missing).
"""

from __future__ import annotations

from enum import Enum

import numpy as np
import pandas as pd


class RaggedEdgeStrategy(str, Enum):
    """How to treat trailing missing months after the last published print."""

    CARRY = "carry"
    AR1 = "ar1"
    LEAVE_MISSING = "leave_missing"


def apply_ragged_edge(
    panel: pd.DataFrame,
    strategy: RaggedEdgeStrategy | str,
    *,
    ar_max_lag: int = 1,
) -> pd.DataFrame:
    """Apply a ragged-edge strategy column-wise to a monthly wide panel.

    Inputs: DataFrame indexed by monthly Period/Timestamp; columns are series
            levels already restricted to as_of knowledge; strategy name/enum;
            ar_max_lag used only for AR(1) (must be 1 in v1).
    Outputs: copy of panel with trailing NaNs after last observation filled
             according to strategy. Interior NaNs are left unchanged.
    Time allowed to know: only values already in ``panel`` (no future prints).
    """
    strat = RaggedEdgeStrategy(strategy)
    if panel.empty:
        return panel.copy()

    out = panel.copy()
    for col in out.columns:
        out[col] = _fill_trailing(out[col], strat, ar_max_lag=ar_max_lag)
    return out


def _fill_trailing(
    series: pd.Series,
    strategy: RaggedEdgeStrategy,
    *,
    ar_max_lag: int,
) -> pd.Series:
    if strategy is RaggedEdgeStrategy.LEAVE_MISSING:
        return series.copy()

    observed = series.dropna()
    if observed.empty:
        return series.copy()

    last_idx = observed.index[-1]
    # Positions strictly after the last observed month.
    trailing_mask = series.index > last_idx
    if not trailing_mask.any():
        return series.copy()

    result = series.copy()
    if strategy is RaggedEdgeStrategy.CARRY:
        result.loc[trailing_mask] = float(observed.iloc[-1])
        return result

    if strategy is RaggedEdgeStrategy.AR1:
        if ar_max_lag != 1:
            raise ValueError("v1 AR ragged fill supports ar_max_lag=1 only")
        filled = _ar1_extrapolate(observed, n_ahead=int(trailing_mask.sum()))
        result.loc[trailing_mask] = filled
        return result

    raise ValueError(f"unknown ragged-edge strategy: {strategy}")


def _ar1_extrapolate(observed: pd.Series, *, n_ahead: int) -> np.ndarray:
    """Simple AR(1) on first differences of levels, then integrate forward.

    Inputs: observed level history (no NaNs); number of months to extrapolate.
    Outputs: length-n_ahead array of level forecasts.
    Time allowed to know: only ``observed`` history.
    """
    values = observed.to_numpy(dtype=float)
    if n_ahead <= 0:
        return np.array([], dtype=float)
    if len(values) < 3:
        # Too short for a stable AR(1); fall back to carry.
        return np.full(n_ahead, values[-1], dtype=float)

    diffs = np.diff(values)
    y = diffs[1:]
    x = diffs[:-1]
    denom = float(np.dot(x, x))
    if denom <= 0 or not np.isfinite(denom):
        phi = 0.0
    else:
        phi = float(np.dot(x, y) / denom)
        # Keep stationary-ish for a first difference AR.
        phi = float(np.clip(phi, -0.99, 0.99))

    last_diff = diffs[-1]
    last_level = values[-1]
    out = np.empty(n_ahead, dtype=float)
    for i in range(n_ahead):
        last_diff = phi * last_diff
        last_level = last_level + last_diff
        out[i] = last_level
    return out
