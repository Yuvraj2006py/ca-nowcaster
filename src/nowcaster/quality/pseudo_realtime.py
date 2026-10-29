"""Pseudo-real-time mode: impute release times from typical publication lags.

Use only when measured release_timestamp vintages are missing. Every imputed
row is flagged as an approximation so features/models can treat it cautiously.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta

import pandas as pd

from nowcaster.quality.frame import normalize_raw_frame
from nowcaster.quality.lags import lag_days_map


def end_of_ref_period(ref_period: date) -> date:
    """Last calendar day of the reference month.

    Inputs: ref_period (first-of-month or any day in the month).
    Outputs: date of month-end.
    Time allowed to know: calendar arithmetic only.
    """
    last_day = monthrange(ref_period.year, ref_period.month)[1]
    return date(ref_period.year, ref_period.month, last_day)


def approximate_release_timestamp(ref_period: date, lag_days: int) -> datetime:
    """Compute approximate public time = ref month-end + lag_days at 12:00 UTC.

    Inputs: reference period; lag days after month-end.
    Outputs: naive UTC datetime used as synthetic release_timestamp.
    Time allowed to know: lag config + calendar; not a measured release.
    """
    pub_day = end_of_ref_period(ref_period) + timedelta(days=lag_days)
    return datetime(pub_day.year, pub_day.month, pub_day.day, 12, 0, 0)


def apply_publication_lags(
    store: pd.DataFrame,
    lag_days_by_series: dict[str, int] | None = None,
    *,
    overwrite_existing: bool = False,
) -> pd.DataFrame:
    """Fill missing release_timestamp using typical lags; flag approximations.

    Inputs: raw store; optional lag map (defaults to typical_lags.yaml).
            overwrite_existing=False keeps measured release times.
    Outputs: DataFrame with RAW_STORE_COLUMNS plus:
             - release_is_approximate (bool)
             - release_source ("measured" | "typical_lag" | "missing_lag")
    Time allowed to know: store values + lag config; does not peek at future
             actuals beyond what is already in the store.
    """
    frame = normalize_raw_frame(store)
    lags = lag_days_by_series if lag_days_by_series is not None else lag_days_map()

    approx_flags: list[bool] = []
    sources: list[str] = []
    releases: list[pd.Timestamp | pd.NaT] = []

    for _, row in frame.iterrows():
        existing = row["release_timestamp"]
        has_measured = pd.notna(existing)
        if has_measured and not overwrite_existing:
            releases.append(pd.Timestamp(existing))
            approx_flags.append(False)
            sources.append("measured")
            continue

        series_id = str(row["series_id"])
        if series_id not in lags:
            releases.append(pd.NaT if not has_measured else pd.Timestamp(existing))
            approx_flags.append(bool(has_measured and overwrite_existing) or not has_measured)
            sources.append("missing_lag" if not has_measured else "measured")
            continue

        synthetic = approximate_release_timestamp(row["ref_period"], lags[series_id])
        releases.append(pd.Timestamp(synthetic))
        approx_flags.append(True)
        sources.append("typical_lag")

    out = frame.copy()
    out["release_timestamp"] = pd.to_datetime(releases)
    out["release_is_approximate"] = approx_flags
    out["release_source"] = pd.Series(sources, dtype="string")
    return out.reset_index(drop=True)


def ensure_release_timestamps(
    store: pd.DataFrame,
    lag_days_by_series: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Return a store usable by as_of: impute only where release is null.

    Inputs: raw store that may lack release_timestamp on some rows.
    Outputs: frame with release times filled via typical lags where needed;
             approximation flags attached.
    Time allowed to know: same as apply_publication_lags.
    """
    return apply_publication_lags(store, lag_days_by_series, overwrite_existing=False)
