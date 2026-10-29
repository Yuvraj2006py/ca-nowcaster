"""Normalize raw-store inputs to the shared RAW_STORE_COLUMNS schema."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime
from typing import Any

import pandas as pd

from nowcaster.contracts import RAW_STORE_COLUMNS, RawObservation

REQUIRED_COLUMNS: tuple[str, ...] = RAW_STORE_COLUMNS


def observations_to_frame(
    rows: Sequence[RawObservation] | Iterable[RawObservation],
) -> pd.DataFrame:
    """Convert RawObservation rows into a typed raw-store DataFrame.

    Inputs: iterable of RawObservation (contract schema).
    Outputs: DataFrame with RAW_STORE_COLUMNS, timezone-naive UTC timestamps.
    Time allowed to know: whatever is already on each RawObservation; no enrichment.
    """
    records = [
        {
            "series_id": r.series_id,
            "ref_period": r.ref_period,
            "value": float(r.value),
            "release_timestamp": r.release_timestamp,
            "retrieved_at": r.retrieved_at,
        }
        for r in rows
    ]
    if not records:
        return empty_raw_frame()
    return normalize_raw_frame(pd.DataFrame.from_records(records))


def empty_raw_frame() -> pd.DataFrame:
    """Empty raw-store frame with correct dtypes.

    Inputs: none.
    Outputs: zero-row DataFrame matching RAW_STORE_COLUMNS.
    Time allowed to know: n/a.
    """
    return pd.DataFrame(
        {
            "series_id": pd.Series(dtype="string"),
            "ref_period": pd.Series(dtype="object"),
            "value": pd.Series(dtype="float64"),
            "release_timestamp": pd.Series(dtype="datetime64[ns]"),
            "retrieved_at": pd.Series(dtype="datetime64[ns]"),
        }
    )


def normalize_raw_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Validate and coerce a DataFrame to the raw-store contract.

    Inputs: DataFrame that must include RAW_STORE_COLUMNS (extras dropped).
    Outputs: cleaned DataFrame with parsed dates/timestamps.
    Time allowed to know: values already present in df; does not invent release times.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"raw store missing columns: {missing}")

    out = df.loc[:, list(REQUIRED_COLUMNS)].copy()
    out["series_id"] = out["series_id"].astype("string")
    out["ref_period"] = out["ref_period"].map(_to_date)
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out["release_timestamp"] = _to_naive_utc_series(out["release_timestamp"])
    out["retrieved_at"] = _to_naive_utc_series(out["retrieved_at"])
    return out.reset_index(drop=True)


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    ts = pd.Timestamp(value)
    return ts.date()


def _to_naive_utc_series(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, utc=True, errors="coerce")
    # Store as naive UTC for simple comparisons across the package.
    return ts.dt.tz_convert("UTC").dt.tz_localize(None)


def as_of_cutoff_timestamp(as_of: date | datetime) -> pd.Timestamp:
    """Inclusive public-knowledge cutoff as a naive-UTC Timestamp.

    Inputs: as_of date (end of calendar day UTC) or datetime.
    Outputs: Timestamp; releases at or before this instant are allowed.
    Time allowed to know: the cutoff itself only.
    """
    # datetime is a subclass of date; check datetime first for clock precision.
    if isinstance(as_of, datetime):
        ts = pd.Timestamp(as_of)
        if ts.tzinfo is not None:
            ts = ts.tz_convert("UTC").tz_localize(None)
        return ts
    # Pure date → inclusive through end of that calendar day (UTC).
    return pd.Timestamp(datetime(as_of.year, as_of.month, as_of.day, 23, 59, 59, 999999))
