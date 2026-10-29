"""Unit tests for monthly transforms."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nowcaster.features.transforms import lag, log_diff, mom_growth, rolling_mean, yoy_growth


def _levels() -> pd.Series:
    idx = pd.period_range("2023-01", periods=15, freq="M")
    return pd.Series(np.linspace(100.0, 114.0, 15), index=idx)


def test_mom_and_log_diff_first_obs_nan() -> None:
    levels = _levels()
    mom = mom_growth(levels)
    ld = log_diff(levels)
    assert np.isnan(mom.iloc[0])
    assert np.isnan(ld.iloc[0])
    expected = (levels.iloc[1] - levels.iloc[0]) / levels.iloc[0]
    assert mom.iloc[1] == pytest.approx(expected)


def test_yoy_needs_twelve_months() -> None:
    yoy = yoy_growth(_levels())
    assert yoy.iloc[:12].isna().all()
    assert not np.isnan(yoy.iloc[12])


def test_rolling_and_lag() -> None:
    levels = _levels()
    roll = rolling_mean(levels, 3)
    assert roll.iloc[:2].isna().all()
    assert roll.iloc[2] == pytest.approx(float(levels.iloc[:3].mean()))
    lagged = lag(levels, 2)
    assert lagged.iloc[:2].isna().all()
    assert lagged.iloc[2] == levels.iloc[0]
