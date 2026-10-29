"""Tests for ragged-edge fill strategies."""

from __future__ import annotations

import numpy as np
import pandas as pd

from nowcaster.features.ragged import RaggedEdgeStrategy, apply_ragged_edge


def _panel() -> pd.DataFrame:
    idx = pd.period_range("2024-01", periods=6, freq="M")
    # Series A observed through March; Series B through May.
    a = pd.Series([1.0, 2.0, 3.0, np.nan, np.nan, np.nan], index=idx)
    b = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, np.nan], index=idx)
    return pd.DataFrame({"a": a, "b": b})


def test_leave_missing_unchanged() -> None:
    panel = _panel()
    out = apply_ragged_edge(panel, RaggedEdgeStrategy.LEAVE_MISSING)
    assert out.equals(panel)


def test_carry_fills_trailing_only() -> None:
    out = apply_ragged_edge(_panel(), "carry")
    assert list(out["a"].iloc[3:]) == [3.0, 3.0, 3.0]
    assert out["b"].iloc[5] == 14.0
    # Interior would stay if present — here no interior gap after first obs.


def test_ar1_extrapolates_trailing() -> None:
    idx = pd.period_range("2024-01", periods=8, freq="M")
    # Linear levels → constant diff → AR(1) continues roughly linearly.
    levels = pd.Series(np.arange(1.0, 7.0), index=idx[:6])
    panel = pd.DataFrame({"x": levels.reindex(idx)})
    out = apply_ragged_edge(panel, RaggedEdgeStrategy.AR1)
    assert out["x"].iloc[5] == 6.0
    assert out["x"].iloc[6] > 6.0
    assert np.isfinite(out["x"].iloc[7])
