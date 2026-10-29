"""Shared fixtures: synthetic raw-store vintages with known release times."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import pytest

from nowcaster.contracts import RawObservation
from nowcaster.quality.frame import observations_to_frame


@pytest.fixture
def leakage_store() -> pd.DataFrame:
    """Store where some vintages become public after 2024-03-15.

    Used by as_of leakage tests: as_of(2024-03-15) must never return the
    March-15-evening or later releases.
    """
    rows = [
        # GDP Jan: released mid-March (before cutoff)
        RawObservation(
            series_id="ca_gdp_basic_prices",
            ref_period=date(2024, 1, 1),
            value=0.2,
            release_timestamp=datetime(2024, 3, 14, 8, 30, 0),
            retrieved_at=datetime(2024, 3, 14, 12, 0, 0),
        ),
        # GDP Feb: released AFTER cutoff — must not appear in as_of(2024-03-15)
        # if we use a morning cutoff; with date cutoff end-of-day it appears.
        # Use an explicitly future release for hard leakage proof:
        RawObservation(
            series_id="ca_gdp_basic_prices",
            ref_period=date(2024, 2, 1),
            value=0.1,
            release_timestamp=datetime(2024, 3, 29, 8, 30, 0),
            retrieved_at=datetime(2024, 3, 29, 12, 0, 0),
        ),
        # Employment Jan: early Feb
        RawObservation(
            series_id="ca_lfs_employment",
            ref_period=date(2024, 1, 1),
            value=20_100_000.0,
            release_timestamp=datetime(2024, 2, 9, 8, 30, 0),
            retrieved_at=datetime(2024, 2, 9, 12, 0, 0),
        ),
        # Employment Feb: early March, before mid-March cutoff
        RawObservation(
            series_id="ca_lfs_employment",
            ref_period=date(2024, 2, 1),
            value=20_150_000.0,
            release_timestamp=datetime(2024, 3, 8, 8, 30, 0),
            retrieved_at=datetime(2024, 3, 8, 12, 0, 0),
        ),
        # Revised employment Feb vintage released after cutoff
        RawObservation(
            series_id="ca_lfs_employment",
            ref_period=date(2024, 2, 1),
            value=20_148_000.0,
            release_timestamp=datetime(2024, 4, 5, 8, 30, 0),
            retrieved_at=datetime(2024, 4, 5, 12, 0, 0),
        ),
    ]
    return observations_to_frame(rows)


@pytest.fixture
def quality_fixture_store() -> pd.DataFrame:
    """Broader fixture exercising validation checks + clean series."""
    rows: list[RawObservation] = []
    # Clean monthly series Jan–Jun 2023
    for month in range(1, 7):
        rows.append(
            RawObservation(
                series_id="fixture_clean_index",
                ref_period=date(2023, month, 1),
                value=100.0 + month,
                release_timestamp=datetime(2023, month, 15, 12, 0, 0),
                retrieved_at=datetime(2023, month, 15, 18, 0, 0),
            )
        )
    # Gap series: missing March
    for month in (1, 2, 4, 5):
        rows.append(
            RawObservation(
                series_id="fixture_gap_series",
                ref_period=date(2023, month, 1),
                value=10.0 * month,
                release_timestamp=datetime(2023, month, 20, 12, 0, 0),
                retrieved_at=datetime(2023, month, 20, 18, 0, 0),
            )
        )
    # Unit change: jumps ~1000x
    rows.extend(
        [
            RawObservation(
                series_id="fixture_unit_change",
                ref_period=date(2023, 1, 1),
                value=1.5,
                release_timestamp=datetime(2023, 2, 1, 12, 0, 0),
                retrieved_at=datetime(2023, 2, 1, 18, 0, 0),
            ),
            RawObservation(
                series_id="fixture_unit_change",
                ref_period=date(2023, 2, 1),
                value=1500.0,
                release_timestamp=datetime(2023, 3, 1, 12, 0, 0),
                retrieved_at=datetime(2023, 3, 1, 18, 0, 0),
            ),
        ]
    )
    # Duplicate vintage key
    rows.extend(
        [
            RawObservation(
                series_id="fixture_dupes",
                ref_period=date(2023, 1, 1),
                value=1.0,
                release_timestamp=datetime(2023, 2, 1, 12, 0, 0),
                retrieved_at=datetime(2023, 2, 1, 18, 0, 0),
            ),
            RawObservation(
                series_id="fixture_dupes",
                ref_period=date(2023, 1, 1),
                value=1.0,
                release_timestamp=datetime(2023, 2, 1, 12, 0, 0),
                retrieved_at=datetime(2023, 2, 1, 18, 0, 0),
            ),
        ]
    )
    # Stale GDP-like series ending long ago
    rows.append(
        RawObservation(
            series_id="ca_gdp_basic_prices",
            ref_period=date(2022, 1, 1),
            value=0.3,
            release_timestamp=datetime(2022, 3, 31, 12, 0, 0),
            retrieved_at=datetime(2022, 3, 31, 18, 0, 0),
        )
    )
    return observations_to_frame(rows)
