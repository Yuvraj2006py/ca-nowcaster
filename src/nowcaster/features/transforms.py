"""Monthly series transformations for leakage-safe feature construction.

All transforms operate on already as-of-filtered level series. They never
consult release timestamps; callers must supply only public knowledge.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def mom_growth(levels: pd.Series) -> pd.Series:
    """Month-over-month percent growth.

    Inputs: monthly level Series indexed by Period[M] or Timestamp (month start).
    Outputs: same index; first observation NaN.
    Time allowed to know: only levels already present in ``levels``.
    """
    # fill_method=None: never forward-fill levels before differencing (that would
    # invent MoM=0 across the ragged edge and break as_of nesting tests).
    return levels.pct_change(periods=1, fill_method=None)


def yoy_growth(levels: pd.Series) -> pd.Series:
    """Year-over-year percent growth (12-month lag).

    Inputs: monthly level Series.
    Outputs: same index; first 12 observations NaN.
    Time allowed to know: only levels already present in ``levels``.
    """
    return levels.pct_change(periods=12, fill_method=None)


def log_diff(levels: pd.Series) -> pd.Series:
    """First difference of natural log levels (approx. continuous MoM growth).

    Inputs: monthly level Series (must be strictly positive where defined).
    Outputs: same index; non-positive levels become NaN before differencing.
    Time allowed to know: only levels already present in ``levels``.
    """
    safe = levels.where(levels > 0)
    return np.log(safe).diff(periods=1)


def rolling_mean(levels: pd.Series, window: int) -> pd.Series:
    """Trailing rolling mean of levels.

    Inputs: monthly level Series; positive integer window.
    Outputs: same index; first ``window - 1`` observations NaN (min_periods=window).
    Time allowed to know: only levels already present in ``levels`` (past window only).
    """
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")
    return levels.rolling(window=window, min_periods=window).mean()


def lag(series: pd.Series, periods: int) -> pd.Series:
    """Shift series forward in calendar time (lag of ``periods`` months).

    Inputs: monthly Series; non-negative integer periods.
    Outputs: value at t equals input at t - periods; leading NaNs for lag > 0.
    Time allowed to know: only values already present (no forward fill here).
    """
    if periods < 0:
        raise ValueError(f"lag periods must be >= 0, got {periods}")
    if periods == 0:
        return series.copy()
    return series.shift(periods)
