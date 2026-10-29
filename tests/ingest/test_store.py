"""Raw store duplicate-prevention tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from nowcaster.contracts import RawObservation
from nowcaster.ingest.store import RawStore


def _row(ref: str, release: str, retrieved: str, value: float = 1.0) -> RawObservation:
    return RawObservation(
        series_id="demo",
        ref_period=date.fromisoformat(ref),
        value=value,
        release_timestamp=datetime.fromisoformat(release).replace(tzinfo=UTC),
        retrieved_at=datetime.fromisoformat(retrieved).replace(tzinfo=UTC),
    )


def test_duckdb_skips_duplicate_vintages(tmp_path: Path) -> None:
    path = tmp_path / "raw.duckdb"
    store = RawStore(path, backend="duckdb")
    first = store.insert_observations(
        [
            _row("2024-01-01", "2024-03-01T08:30:00", "2024-03-01T12:00:00", 10.0),
            _row("2024-02-01", "2024-04-01T08:30:00", "2024-04-01T12:00:00", 11.0),
        ]
    )
    assert first.inserted == 2
    second = store.insert_observations(
        [
            _row("2024-01-01", "2024-03-01T08:30:00", "2024-05-01T12:00:00", 10.0),
            _row("2024-02-01", "2024-04-01T08:30:00", "2024-05-01T12:00:00", 11.0),
        ]
    )
    assert second.inserted == 0
    assert second.skipped_duplicates == 2
    assert store.count_rows() == 2
    store.close()


def test_revision_vintage_is_appended(tmp_path: Path) -> None:
    path = tmp_path / "raw.sqlite"
    store = RawStore(path, backend="sqlite")
    store.insert_observations(
        [_row("2024-01-01", "2024-03-01T08:30:00", "2024-03-01T12:00:00", 10.0)]
    )
    result = store.insert_observations(
        [_row("2024-01-01", "2024-04-01T08:30:00", "2024-04-01T12:00:00", 10.5)]
    )
    assert result.inserted == 1
    assert store.count_rows() == 2
    store.close()
