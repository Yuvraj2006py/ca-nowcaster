"""Shared fixtures for Phase 2 baseline tests.

Inputs: synthetic MoM growth CSV under tests/fixtures/models/.
Outputs: X scaffold (empty feature columns) and y Series for fit/predict.
Time allowed to know: fixture values only (no live releases).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "models"


@pytest.fixture
def mom_frame() -> pd.DataFrame:
    """Load synthetic monthly MoM growth with a DatetimeIndex."""
    path = FIXTURES / "synthetic_mom_growth.csv"
    frame = pd.read_csv(path, parse_dates=["ref_month"])
    frame = frame.set_index("ref_month").sort_index()
    return frame


@pytest.fixture
def train_xy(mom_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """First 18 months as training X (empty cols) and y."""
    train = mom_frame.iloc[:18]
    y = train["mom_growth"]
    # Empty feature frame: baselines ignore columns; harness still passes X.
    X = pd.DataFrame(index=train.index)
    return X, y


@pytest.fixture
def test_x(mom_frame: pd.DataFrame) -> pd.DataFrame:
    """Next 3 months as prediction scaffold (no feature values required)."""
    return pd.DataFrame(index=mom_frame.iloc[18:21].index)
