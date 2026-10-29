"""Append-only raw observation store (DuckDB by default, SQLite fallback).

Inputs: RawObservation rows from contracts.
Outputs: persisted vintages; counts of inserted vs skipped duplicates.
Time allowed to know: release_timestamp and retrieved_at as provided by callers;
this module does not alter economic timestamps.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from nowcaster.contracts import RAW_STORE_COLUMNS, RawObservation

logger = logging.getLogger(__name__)

Backend = Literal["duckdb", "sqlite"]

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS raw_observations (
    series_id VARCHAR NOT NULL,
    ref_period DATE NOT NULL,
    value DOUBLE NOT NULL,
    release_timestamp TIMESTAMP NOT NULL,
    retrieved_at TIMESTAMP NOT NULL
)
"""

# Vintage identity excludes retrieved_at so a second identical refresh does not duplicate.
UNIQUE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_obs_vintage
ON raw_observations (series_id, ref_period, release_timestamp)
"""


@dataclass(frozen=True)
class InsertResult:
    attempted: int
    inserted: int
    skipped_duplicates: int


class RawStore:
    """DuckDB/SQLite store for append-only raw vintages."""

    def __init__(self, path: Path | str | None = None, *, backend: Backend | None = None) -> None:
        env_path = os.environ.get("RAW_STORE_PATH", "data/raw.duckdb")
        self.path = Path(path) if path is not None else Path(env_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if backend is None:
            backend = "sqlite" if self.path.suffix in {".sqlite", ".db"} else "duckdb"
        self.backend: Backend = backend
        self._conn: object | None = None
        self._connect()
        self._ensure_schema()

    def _connect(self) -> None:
        if self.backend == "duckdb":
            import duckdb

            self._conn = duckdb.connect(str(self.path))
        else:
            self._conn = sqlite3.connect(str(self.path))
            self._conn.execute("PRAGMA journal_mode=WAL")

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> RawStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _ensure_schema(self) -> None:
        assert self._conn is not None
        self._conn.execute(CREATE_SQL)
        # DuckDB unique index syntax is supported; SQLite too.
        try:
            self._conn.execute(UNIQUE_INDEX_SQL)
        except Exception as exc:  # noqa: BLE001 — backend-specific IF NOT EXISTS quirks
            logger.debug("Unique index ensure note: %s", exc)
        if self.backend == "sqlite":
            self._conn.commit()

    def insert_observations(self, rows: Iterable[RawObservation]) -> InsertResult:
        """Insert vintages; skip rows that collide on vintage identity.

        Inputs: iterable of RawObservation.
        Outputs: InsertResult with attempted/inserted/skipped counts.
        Time allowed to know: stamps already on each RawObservation.
        """
        assert self._conn is not None
        attempted = 0
        inserted = 0
        skipped = 0
        # INSERT OR IGNORE skips vintage collisions on both DuckDB and SQLite.
        sql = """
            INSERT OR IGNORE INTO raw_observations
            (series_id, ref_period, value, release_timestamp, retrieved_at)
            VALUES (?, ?, ?, ?, ?)
        """
        before = self.count_rows()
        batch: list[tuple[object, ...]] = []
        for row in rows:
            attempted += 1
            batch.append(
                (
                    row.series_id,
                    row.ref_period.isoformat(),
                    float(row.value),
                    _ts(row.release_timestamp),
                    _ts(row.retrieved_at),
                )
            )
        if batch:
            if self.backend == "duckdb":
                self._conn.executemany(sql, batch)
            else:
                assert self._conn is not None
                self._conn.executemany(sql, batch)
                self._conn.commit()
        after = self.count_rows()
        inserted = after - before
        skipped = attempted - inserted
        return InsertResult(attempted=attempted, inserted=inserted, skipped_duplicates=skipped)

    def count_rows(self) -> int:
        assert self._conn is not None
        result = self._conn.execute("SELECT COUNT(*) FROM raw_observations")
        row = result.fetchone() if hasattr(result, "fetchone") else next(result)
        return int(row[0])

    def fetch_all(self) -> list[dict[str, object]]:
        """Return all rows as dicts (for tests / debugging)."""
        assert self._conn is not None
        # Static SQL (contract columns only) — avoids Bandit B608 on dynamic SQL.
        expected = (
            "series_id",
            "ref_period",
            "value",
            "release_timestamp",
            "retrieved_at",
        )
        if RAW_STORE_COLUMNS != expected:
            raise RuntimeError("RAW_STORE_COLUMNS drifted from fetch_all SELECT list")
        result = self._conn.execute(
            "SELECT series_id, ref_period, value, release_timestamp, retrieved_at "
            "FROM raw_observations ORDER BY 1, 2, 4"
        )
        rows = result.fetchall()
        out: list[dict[str, object]] = []
        for row in rows:
            out.append(dict(zip(RAW_STORE_COLUMNS, row, strict=True)))
        return out


def _ts(value: datetime) -> str:
    if value.tzinfo is not None:
        return value.isoformat()
    return value.isoformat()


def parse_ref_period(value: str | date | datetime) -> date:
    """Normalize a reference period string/date to a date (first of month if monthly)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if len(text) == 7 and text[4] == "-":
        text = f"{text}-01"
    return date.fromisoformat(text[:10])
