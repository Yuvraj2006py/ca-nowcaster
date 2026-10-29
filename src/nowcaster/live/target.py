"""Extract leakage-safe primary-target MoM growth for live fit/predict/score.

Uses quality.as_of and features.transforms.mom_growth only — does not edit
feature or model packages.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

from nowcaster.features.transforms import mom_growth
from nowcaster.live.production import PRIMARY_TARGET_SERIES_ID
from nowcaster.quality.release_calendar import as_of


@dataclass(frozen=True)
class TargetHistory:
    """Ordered MoM growth history known by an as_of cutoff.

    Inputs: as_of-filtered GDP levels → MoM.
    Outputs: series indexed by ref_month (Period[M]); last published month.
    Time allowed to know: only releases with release_timestamp <= as_of_date.
    """

    series_id: str
    as_of_date: date
    mom: pd.Series  # Period[M] index; finite MoM values only
    last_published_ref_month: date | None


def target_mom_as_of(
    store: pd.DataFrame,
    as_of_date: date | datetime,
    *,
    series_id: str = PRIMARY_TARGET_SERIES_ID,
) -> TargetHistory:
    """Build primary-target MoM growth series known by as_of_date.

    Inputs: raw store DataFrame; inclusive as_of cutoff; target series_id.
    Outputs: TargetHistory with finite MoM values time-ordered.
    Time allowed to know: only values with release_timestamp <= as_of_date.
    """
    if isinstance(as_of_date, datetime):
        as_of_day = as_of_date.date()
    else:
        as_of_day = as_of_date

    view = as_of(store, as_of_day, series_id=series_id)
    if view.empty:
        return TargetHistory(
            series_id=series_id,
            as_of_date=as_of_day,
            mom=pd.Series(dtype="float64"),
            last_published_ref_month=None,
        )

    levels = (
        view.assign(ref_month=lambda d: pd.PeriodIndex(pd.to_datetime(d["ref_period"]), freq="M"))
        .sort_values(["ref_month", "release_timestamp"])
        .drop_duplicates("ref_month", keep="last")
        .set_index("ref_month")["value"]
        .astype(float)
        .sort_index()
    )
    # Continuous monthly index so MoM is calendar-correct.
    full_index = pd.period_range(levels.index.min(), levels.index.max(), freq="M")
    levels = levels.reindex(full_index)
    mom = mom_growth(levels).dropna()

    last_pub: date | None = None
    if len(levels.dropna()) > 0:
        last_period = levels.dropna().index.max()
        last_pub = date(last_period.year, last_period.month, 1)

    return TargetHistory(
        series_id=series_id,
        as_of_date=as_of_day,
        mom=mom,
        last_published_ref_month=last_pub,
    )


def next_unpublished_month(history: TargetHistory) -> date | None:
    """Return the first calendar month after the last published target month.

    Inputs: TargetHistory from target_mom_as_of.
    Outputs: date (first of month) to nowcast, or None if no published history.
    Time allowed to know: last_published_ref_month only (already as_of-filtered).
    """
    if history.last_published_ref_month is None:
        return None
    period = pd.Period(history.last_published_ref_month, freq="M") + 1
    return date(period.year, period.month, 1)


def actual_mom_for_month(
    store: pd.DataFrame,
    target_ref_month: date,
    *,
    as_of_date: date | datetime,
    series_id: str = PRIMARY_TARGET_SERIES_ID,
) -> float | None:
    """Return realized MoM for target_ref_month if published by as_of_date.

    Inputs: raw store; target month; scoring as_of cutoff.
    Outputs: float MoM or None if that month's levels are not yet public.
    Time allowed to know: only releases <= as_of_date.
    """
    history = target_mom_as_of(store, as_of_date, series_id=series_id)
    if history.mom.empty:
        return None
    key = pd.Period(target_ref_month, freq="M")
    if key not in history.mom.index:
        return None
    value = history.mom.loc[key]
    if pd.isna(value):
        return None
    return float(value)
