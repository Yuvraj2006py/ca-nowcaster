"""Phase 1 gate pieces owned by Data Quality: as_of leakage.

Ingestion owns the 'one command refreshes raw store' half of Phase 1.
This module asserts the timing invariant: as_of(date) never returns a value
whose release_timestamp is after date.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from nowcaster.contracts import RAW_STORE_COLUMNS, RawObservation
from nowcaster.quality import as_of, assert_no_as_of_leakage
from nowcaster.quality.frame import observations_to_frame

ROOT = Path(__file__).resolve().parents[2]


def _gate_store() -> pd.DataFrame:
    """Deterministic fixture with known pre/post cutoff releases."""
    return observations_to_frame(
        [
            RawObservation(
                series_id="gate_series_a",
                ref_period=date(2024, 1, 1),
                value=1.0,
                release_timestamp=datetime(2024, 2, 10, 8, 0, 0),
                retrieved_at=datetime(2024, 2, 10, 9, 0, 0),
            ),
            RawObservation(
                series_id="gate_series_a",
                ref_period=date(2024, 2, 1),
                value=2.0,
                release_timestamp=datetime(2024, 3, 10, 8, 0, 0),
                retrieved_at=datetime(2024, 3, 10, 9, 0, 0),
            ),
            RawObservation(
                series_id="gate_series_a",
                ref_period=date(2024, 2, 1),
                value=2.1,
                release_timestamp=datetime(2024, 4, 10, 8, 0, 0),
                retrieved_at=datetime(2024, 4, 10, 9, 0, 0),
            ),
            RawObservation(
                series_id="gate_series_b",
                ref_period=date(2024, 1, 1),
                value=10.0,
                release_timestamp=datetime(2024, 5, 1, 0, 0, 0),
                retrieved_at=datetime(2024, 5, 1, 1, 0, 0),
            ),
        ]
    )


@pytest.mark.parametrize(
    "cutoff",
    [
        date(2024, 3, 15),
        datetime(2024, 3, 10, 8, 0, 0),
        date(2024, 2, 1),
        datetime(2023, 12, 31, 23, 59, 59),
    ],
)
def test_phase_1_as_of_never_returns_future_releases(cutoff: date | datetime) -> None:
    """Gate: every row from as_of has release_timestamp <= cutoff."""
    store = _gate_store()
    view = as_of(store, cutoff)
    assert list(view.columns) == list(RAW_STORE_COLUMNS)

    if isinstance(cutoff, datetime):
        cutoff_ts = pd.Timestamp(cutoff)
    else:
        cutoff_ts = pd.Timestamp(
            datetime(cutoff.year, cutoff.month, cutoff.day, 23, 59, 59, 999999)
        )

    if view.empty:
        return

    leaked = view["release_timestamp"] > cutoff_ts
    assert not leaked.any(), (
        f"as_of leakage at cutoff={cutoff!r}:\n"
        f"{view.loc[leaked, ['series_id', 'ref_period', 'release_timestamp']]}"
    )
    assert_no_as_of_leakage(store, cutoff)


def test_phase_1_as_of_picks_latest_vintage_not_future_revision() -> None:
    store = _gate_store()
    view = as_of(store, date(2024, 3, 15))
    row = view.loc[
        (view["series_id"] == "gate_series_a") & (view["ref_period"] == date(2024, 2, 1))
    ].iloc[0]
    assert float(row["value"]) == 2.0
    assert pd.Timestamp(row["release_timestamp"]) == pd.Timestamp("2024-03-10 08:00:00")


def test_phase_1_quality_package_and_report_exist() -> None:
    required = [
        "src/nowcaster/quality/release_calendar.py",
        "src/nowcaster/quality/validate.py",
        "src/nowcaster/quality/pseudo_realtime.py",
        "src/nowcaster/quality/typical_lags.yaml",
        "docs/quality_report.md",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Phase 1 quality artifacts missing: {missing}"
