"""Unit tests for as_of and release calendar."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from nowcaster.quality import as_of, assert_no_as_of_leakage, earliest_release, release_calendar


def test_as_of_excludes_releases_after_cutoff(leakage_store: pd.DataFrame) -> None:
    cutoff = date(2024, 3, 15)
    view = as_of(leakage_store, cutoff)
    cutoff_ts = pd.Timestamp(datetime(2024, 3, 15, 23, 59, 59, 999999))
    assert (view["release_timestamp"] <= cutoff_ts).all()
    # Feb GDP released 2024-03-29 must be absent
    gdp = view.loc[view["series_id"] == "ca_gdp_basic_prices"]
    assert set(gdp["ref_period"]) == {date(2024, 1, 1)}
    # Feb employment uses March 8 vintage, not April revision
    emp = view.loc[
        (view["series_id"] == "ca_lfs_employment") & (view["ref_period"] == date(2024, 2, 1))
    ]
    assert len(emp) == 1
    assert float(emp.iloc[0]["value"]) == 20_150_000.0


def test_as_of_datetime_cutoff_is_inclusive(leakage_store: pd.DataFrame) -> None:
    cutoff = datetime(2024, 3, 14, 8, 30, 0)
    view = as_of(leakage_store, cutoff)
    assert (view["release_timestamp"] <= pd.Timestamp(cutoff)).all()
    assert date(2024, 1, 1) in set(
        view.loc[view["series_id"] == "ca_gdp_basic_prices", "ref_period"]
    )


def test_assert_no_as_of_leakage_passes(leakage_store: pd.DataFrame) -> None:
    assert_no_as_of_leakage(leakage_store, date(2024, 3, 15))


def test_release_calendar_earliest(leakage_store: pd.DataFrame) -> None:
    cal = release_calendar(leakage_store, series_id="ca_lfs_employment")
    feb = cal.loc[cal["ref_period"] == date(2024, 2, 1)].iloc[0]
    assert pd.Timestamp(feb["release_timestamp"]) == pd.Timestamp("2024-03-08 08:30:00")
    assert earliest_release(leakage_store, "ca_lfs_employment", date(2024, 2, 1)) == pd.Timestamp(
        "2024-03-08 08:30:00"
    )
