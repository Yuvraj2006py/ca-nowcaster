"""Shared fixtures for Phase 2 baseline and Phase 3 candidate tests.

Inputs: synthetic MoM growth / feature CSVs under tests/fixtures/models/.
Outputs: X/y frames for fit/predict.
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
def feature_frame() -> pd.DataFrame:
    """Load synthetic features + MoM growth for Phase 3 candidates."""
    path = FIXTURES / "synthetic_features.csv"
    frame = pd.read_csv(path, parse_dates=["ref_month"])
    frame = frame.set_index("ref_month").sort_index()
    return frame


@pytest.fixture
def train_xy(mom_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """First 18 months as training X (empty cols) and y — baselines."""
    train = mom_frame.iloc[:18]
    y = train["mom_growth"]
    X = pd.DataFrame(index=train.index)
    return X, y


@pytest.fixture
def test_x(mom_frame: pd.DataFrame) -> pd.DataFrame:
    """Next 3 months as prediction scaffold (no feature values required)."""
    return pd.DataFrame(index=mom_frame.iloc[18:21].index)


@pytest.fixture
def candidate_train_xy(feature_frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """First 20 months with real feature columns for Phase 3 candidates."""
    train = feature_frame.iloc[:20]
    y = train["mom_growth"]
    X = train.drop(columns=["mom_growth"])
    return X, y


@pytest.fixture
def candidate_test_x(feature_frame: pd.DataFrame) -> pd.DataFrame:
    """Next 2 months of features for candidate predict."""
    return feature_frame.iloc[20:22].drop(columns=["mom_growth"])
