"""Release calendar helpers and as_of views over the raw store.

Mission: the model must only ever see what the world knew at the time.
"""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from nowcaster.contracts import RAW_STORE_COLUMNS
from nowcaster.quality.frame import as_of_cutoff_timestamp, normalize_raw_frame


def earliest_release(
    store: pd.DataFrame,
    series_id: str,
    ref_period: date,
) -> pd.Timestamp | None:
    """Return the earliest measured release_timestamp for one observation.

    Inputs: raw store (RAW_STORE_COLUMNS); series_id; reference month date.
    Outputs: earliest public release Timestamp, or None if absent.
    Time allowed to know: release times already stored for that observation.
    """
    frame = normalize_raw_frame(store)
    mask = (frame["series_id"] == series_id) & (frame["ref_period"] == ref_period)
    subset = frame.loc[mask, "release_timestamp"].dropna()
    if subset.empty:
        return None
    return pd.Timestamp(subset.min())


def release_calendar(store: pd.DataFrame, series_id: str | None = None) -> pd.DataFrame:
    """Build (series_id, ref_period) -> earliest release_timestamp table.

    Inputs: raw store; optional series_id filter.
    Outputs: DataFrame columns series_id, ref_period, release_timestamp
             (earliest public time per observation key).
    Time allowed to know: only release_timestamps present in the store.
    """
    frame = normalize_raw_frame(store)
    if series_id is not None:
        frame = frame.loc[frame["series_id"] == series_id]
    if frame.empty:
        return pd.DataFrame(
            {
                "series_id": pd.Series(dtype="string"),
                "ref_period": pd.Series(dtype="object"),
                "release_timestamp": pd.Series(dtype="datetime64[ns]"),
            }
        )
    grouped = (
        frame.groupby(["series_id", "ref_period"], sort=True, as_index=False)["release_timestamp"]
        .min()
        .rename(columns={"release_timestamp": "release_timestamp"})
    )
    return grouped


def as_of(
    store: pd.DataFrame,
    as_of_date: date | datetime,
    series_id: str | None = None,
) -> pd.DataFrame:
    """Return the latest vintage of each observation known by as_of_date.

    For each (series_id, ref_period), selects the row with the greatest
    release_timestamp among those with release_timestamp <= cutoff. Ties break
    on retrieved_at (latest fetch of that vintage).

    Inputs: raw store conforming to RAW_STORE_COLUMNS; inclusive as_of cutoff;
            optional series_id filter.
    Outputs: DataFrame with RAW_STORE_COLUMNS (at most one row per key).
    Time allowed to know: ONLY values with release_timestamp <= cutoff.
             Never returns a row whose release is after as_of_date.
    """
    frame = normalize_raw_frame(store)
    if series_id is not None:
        frame = frame.loc[frame["series_id"] == series_id].copy()
    else:
        frame = frame.copy()

    if frame.empty:
        return normalize_raw_frame(frame)

    cutoff = as_of_cutoff_timestamp(as_of_date)
    known = frame.loc[frame["release_timestamp"].notna() & (frame["release_timestamp"] <= cutoff)]
    if known.empty:
        return normalize_raw_frame(known)

    # Latest vintage per key: sort so last row wins.
    ordered = known.sort_values(
        by=["series_id", "ref_period", "release_timestamp", "retrieved_at"],
        ascending=True,
        kind="mergesort",
    )
    latest = ordered.drop_duplicates(subset=["series_id", "ref_period"], keep="last")
    latest = latest.loc[:, list(RAW_STORE_COLUMNS)].reset_index(drop=True)

    # Hard invariant: no leakage past the cutoff.
    leaked = latest["release_timestamp"] > cutoff
    if leaked.any():
        raise AssertionError(
            f"as_of leakage: {int(leaked.sum())} rows have release_timestamp after {cutoff}"
        )
    return latest


def assert_no_as_of_leakage(store: pd.DataFrame, as_of_date: date | datetime) -> None:
    """Raise AssertionError if as_of(store, as_of_date) contains future releases.

    Inputs: raw store; as_of cutoff.
    Outputs: None on success.
    Time allowed to know: same as as_of.
    """
    view = as_of(store, as_of_date)
    cutoff = as_of_cutoff_timestamp(as_of_date)
    if view.empty:
        return
    leaked = view["release_timestamp"] > cutoff
    if leaked.any():
        bad = view.loc[leaked, ["series_id", "ref_period", "release_timestamp"]]
        raise AssertionError(f"as_of leakage detected:\n{bad}")
