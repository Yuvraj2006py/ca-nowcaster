"""Shared fixtures for evaluation harness tests."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def synthetic_panel() -> tuple[pd.DataFrame, pd.Series, dict[date, date]]:
    """Leakage-safe synthetic monthly panel with COVID months and a long history.

    60 months: 2018-01 .. 2022-12. Holdout = final 24 (2021-01 .. 2022-12).
    Train/eval pool = 36 months. COVID shocks Mar–Aug 2020 sit inside the pool.

    Inputs: none (deterministic RNG).
    Outputs: (X, y, as_of_by_month).
    Time allowed to know: synthetic only; as_of is month-end + 2 months.
    """
    rng = np.random.default_rng(42)
    months = pd.period_range("2018-01", "2022-12", freq="M")
    index = pd.Index([m.to_timestamp().date() for m in months], name="ref_month")
    # Mild AR process + noise; COVID months get large negative shocks.
    y_vals = np.zeros(len(index))
    for i in range(len(index)):
        prev = y_vals[i - 1] if i else 0.0
        y_vals[i] = 0.1 * prev + rng.normal(0.0, 0.2)
        d = index[i]
        if d.year == 2020 and 3 <= d.month <= 8:
            y_vals[i] -= 1.5 + 0.3 * (d.month - 3)
    # Features: lag-1 target proxy + a contemporaneous indicator (synthetic).
    x0 = np.roll(y_vals, 1)
    x0[0] = 0.0
    x1 = y_vals + rng.normal(0.0, 0.05, size=len(y_vals))
    X = pd.DataFrame({"lag1": x0, "indicator": x1}, index=index)
    y = pd.Series(y_vals, index=index, name="gdp_mom")
    as_of: dict[date, date] = {}
    for m in index:
        ts = pd.Timestamp(m) + pd.offsets.MonthEnd(0) + pd.DateOffset(months=2)
        as_of[m] = ts.date()
    return X, y, as_of
