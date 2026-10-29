"""Fixtures: multi-month GDP (+ indicators) with staggered releases for live dry-run."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from nowcaster.contracts import RawObservation
from nowcaster.quality.frame import observations_to_frame


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def _monthly_levels(
    series_id: str,
    start: date,
    values: list[float],
    *,
    release_lag_months: int,
    release_day: int,
) -> list[RawObservation]:
    rows: list[RawObservation] = []
    year, month = start.year, start.month
    for value in values:
        ref = date(year, month, 1)
        ry, rm = _add_months(year, month, release_lag_months)
        day = min(release_day, 28)
        release_ts = datetime(ry, rm, day, 8, 30, 0)
        retrieved = datetime(ry, rm, day, 12, 30, 0)
        rows.append(
            RawObservation(
                series_id=series_id,
                ref_period=ref,
                value=float(value),
                release_timestamp=release_ts,
                retrieved_at=retrieved,
            )
        )
        year, month = _add_months(year, month, 1)
    return rows


@pytest.fixture
def live_store() -> pd.DataFrame:
    """24 months of GDP + employment with GDP published ~2 months later.

    Predict as_of mid-sample (before a month's GDP release); score after release.
    """
    n = 24
    # Mild AR(1)-like MoM in levels via cumulative growth.
    gdp = [2_000_000.0]
    for i in range(1, n):
        gdp.append(gdp[-1] * (1.0 + 0.002 * ((-1) ** i)))
    emp = [20_000_000.0 + 5_000 * i for i in range(n)]

    rows: list[RawObservation] = []
    rows.extend(
        _monthly_levels(
            "ca_gdp_basic_prices",
            date(2022, 1, 1),
            gdp,
            release_lag_months=2,
            release_day=28,
        )
    )
    rows.extend(
        _monthly_levels(
            "ca_lfs_employment",
            date(2022, 1, 1),
            emp,
            release_lag_months=1,
            release_day=8,
        )
    )
    return observations_to_frame(rows)


@pytest.fixture
def live_series_meta() -> dict[str, dict[str, str]]:
    return {
        "ca_gdp_basic_prices": {"source": "statcan", "target_role": "primary_target"},
        "ca_lfs_employment": {"source": "statcan", "target_role": "indicator"},
    }
