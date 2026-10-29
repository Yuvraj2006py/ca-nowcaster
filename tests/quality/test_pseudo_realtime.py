"""Pseudo-real-time lag imputation tests."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from nowcaster.contracts import RawObservation
from nowcaster.quality import apply_publication_lags, approximate_release_timestamp, as_of
from nowcaster.quality.frame import observations_to_frame


def test_approximate_release_timestamp_month_end_plus_lag() -> None:
    ts = approximate_release_timestamp(date(2024, 1, 1), 60)
    assert ts == datetime(2024, 3, 31, 12, 0, 0)


def test_apply_lags_flags_approximation_and_preserves_measured() -> None:
    rows = [
        RawObservation(
            series_id="ca_cpi_all_items",
            ref_period=date(2024, 1, 1),
            value=158.0,
            release_timestamp=datetime(2024, 2, 20, 8, 30, 0),
            retrieved_at=datetime(2024, 2, 20, 12, 0, 0),
        ),
        RawObservation(
            series_id="ca_cpi_all_items",
            ref_period=date(2024, 2, 1),
            value=158.5,
            release_timestamp=datetime(2099, 1, 1),  # placeholder overwritten below
            retrieved_at=datetime(2024, 3, 1, 12, 0, 0),
        ),
    ]
    store = observations_to_frame(rows)
    # Simulate missing release on Feb row
    store.loc[store["ref_period"] == date(2024, 2, 1), "release_timestamp"] = pd.NaT

    out = apply_publication_lags(store, {"ca_cpi_all_items": 18})
    jan = out.loc[out["ref_period"] == date(2024, 1, 1)].iloc[0]
    feb = out.loc[out["ref_period"] == date(2024, 2, 1)].iloc[0]
    assert bool(jan["release_is_approximate"]) is False
    assert jan["release_source"] == "measured"
    assert bool(feb["release_is_approximate"]) is True
    assert feb["release_source"] == "typical_lag"
    assert pd.Timestamp(feb["release_timestamp"]) == pd.Timestamp("2024-03-18 12:00:00")


def test_as_of_respects_imputed_lags() -> None:
    store = observations_to_frame(
        [
            RawObservation(
                series_id="ca_retail_trade",
                ref_period=date(2024, 1, 1),
                value=1.0,
                release_timestamp=datetime(2024, 1, 1),  # will clear
                retrieved_at=datetime(2024, 5, 1),
            )
        ]
    )
    store["release_timestamp"] = pd.NaT
    timed = apply_publication_lags(store, {"ca_retail_trade": 52})
    # Expected release ~ 2024-01-31 + 52d = 2024-03-23
    before = as_of(timed, date(2024, 3, 1))
    after = as_of(timed, date(2024, 3, 23))
    assert before.empty
    assert len(after) == 1
