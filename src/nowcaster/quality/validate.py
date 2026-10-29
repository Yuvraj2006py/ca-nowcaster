"""Validation checks over the raw store (append-only vintages)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import pandas as pd

from nowcaster.quality.frame import normalize_raw_frame
from nowcaster.quality.lags import lag_days_map
from nowcaster.quality.pseudo_realtime import end_of_ref_period
from nowcaster.quality.release_calendar import as_of
from nowcaster.quality.types import CheckKind, QualityIssue, Severity


def check_duplicated_rows(store: pd.DataFrame) -> list[QualityIssue]:
    """Flag exact duplicate vintage keys and fully identical rows.

    Inputs: raw store.
    Outputs: issues for duplicated (series_id, ref_period, release_timestamp)
             keys and fully duplicate rows.
    Time allowed to know: store contents only.
    """
    frame = normalize_raw_frame(store)
    issues: list[QualityIssue] = []
    if frame.empty:
        return issues

    key_cols = ["series_id", "ref_period", "release_timestamp"]
    dup_keys = frame.duplicated(subset=key_cols, keep=False)
    if dup_keys.any():
        n = int(frame.loc[dup_keys].groupby(key_cols, dropna=False).ngroups)
        issues.append(
            QualityIssue(
                kind=CheckKind.DUPLICATED_ROWS,
                severity=Severity.ERROR,
                series_id=None,
                message=f"{n} duplicated vintage key group(s) "
                f"(series_id, ref_period, release_timestamp).",
                details={"n_groups": n, "n_rows": int(dup_keys.sum())},
            )
        )

    full_dup = frame.duplicated(keep=False)
    if full_dup.any():
        issues.append(
            QualityIssue(
                kind=CheckKind.DUPLICATED_ROWS,
                severity=Severity.WARNING,
                series_id=None,
                message=f"{int(full_dup.sum())} fully identical row(s) present.",
                details={"n_rows": int(full_dup.sum())},
            )
        )
    return issues


def check_missing_periods(
    store: pd.DataFrame,
    *,
    as_of_date: date | datetime | None = None,
    frequency: str = "monthly",
) -> list[QualityIssue]:
    """Detect gaps in the monthly reference-period sequence per series.

    Inputs: raw store; optional as_of_date (uses as_of view); frequency
            (only 'monthly' supported in v1).
    Outputs: one issue per series with missing months inside its observed span.
    Time allowed to know: if as_of_date set, only releases <= as_of_date.
    """
    if frequency != "monthly":
        raise ValueError("v1 missing-period check supports frequency='monthly' only")

    frame = normalize_raw_frame(store)
    if as_of_date is not None:
        frame = as_of(frame, as_of_date)
    issues: list[QualityIssue] = []
    if frame.empty:
        return issues

    for series_id, group in frame.groupby("series_id", sort=True):
        periods = sorted({_month_start(p) for p in group["ref_period"]})
        if len(periods) < 2:
            continue
        expected = _monthly_range(periods[0], periods[-1])
        missing = [p for p in expected if p not in set(periods)]
        if missing:
            issues.append(
                QualityIssue(
                    kind=CheckKind.MISSING_PERIODS,
                    severity=Severity.WARNING,
                    series_id=str(series_id),
                    message=f"{len(missing)} missing monthly ref_period(s) "
                    f"between {periods[0]} and {periods[-1]}.",
                    details={
                        "missing": [p.isoformat() for p in missing[:24]],
                        "n_missing": len(missing),
                    },
                )
            )
    return issues


def check_level_breaks(
    store: pd.DataFrame,
    *,
    as_of_date: date | datetime | None = None,
    abs_pct_threshold: float = 0.25,
) -> list[QualityIssue]:
    """Flag sudden month-to-month level jumps beyond a threshold.

    Inputs: raw store; optional as_of view; absolute percent change threshold
            (default 25%).
    Outputs: warning per series/period where |Δ|/|prev| exceeds threshold
             (skips near-zero previous values).
    Time allowed to know: if as_of_date set, only releases <= as_of_date.
    """
    frame = _latest_levels(store, as_of_date)
    issues: list[QualityIssue] = []
    for series_id, group in frame.groupby("series_id", sort=True):
        ordered = group.sort_values("ref_period")
        prev_value: float | None = None
        prev_period: date | None = None
        for _, row in ordered.iterrows():
            value = float(row["value"])
            period = row["ref_period"]
            if prev_value is not None and abs(prev_value) > 1e-12:
                pct = abs(value - prev_value) / abs(prev_value)
                if pct > abs_pct_threshold:
                    issues.append(
                        QualityIssue(
                            kind=CheckKind.LEVEL_BREAK,
                            severity=Severity.WARNING,
                            series_id=str(series_id),
                            message=(
                                f"Level break {prev_period} → {period}: "
                                f"{pct:.1%} change (threshold {abs_pct_threshold:.0%})."
                            ),
                            details={
                                "from_period": prev_period.isoformat() if prev_period else None,
                                "to_period": period.isoformat(),
                                "from_value": prev_value,
                                "to_value": value,
                                "abs_pct_change": pct,
                            },
                        )
                    )
            prev_value = value
            prev_period = period
    return issues


def check_unit_changes(
    store: pd.DataFrame,
    *,
    as_of_date: date | datetime | None = None,
    ratio_thresholds: tuple[float, ...] = (10.0, 100.0, 1000.0),
    tolerance: float = 0.05,
) -> list[QualityIssue]:
    """Flag successive values whose ratio is near a round scale factor.

    Inputs: raw store; optional as_of; candidate scale ratios (e.g. 1000 for
            thousands→units); relative tolerance around each ratio.
    Outputs: error-severity issues when a unit rescale is suspected.
    Time allowed to know: if as_of_date set, only releases <= as_of_date.
    """
    frame = _latest_levels(store, as_of_date)
    issues: list[QualityIssue] = []
    for series_id, group in frame.groupby("series_id", sort=True):
        ordered = group.sort_values("ref_period")
        prev_value: float | None = None
        prev_period: date | None = None
        for _, row in ordered.iterrows():
            value = float(row["value"])
            period = row["ref_period"]
            if prev_value is not None and abs(prev_value) > 1e-12 and abs(value) > 1e-12:
                ratio = abs(value / prev_value)
                for target in ratio_thresholds:
                    if (
                        abs(ratio - target) / target <= tolerance
                        or abs(ratio - (1.0 / target)) / (1.0 / target) <= tolerance
                    ):
                        issues.append(
                            QualityIssue(
                                kind=CheckKind.UNIT_CHANGE,
                                severity=Severity.ERROR,
                                series_id=str(series_id),
                                message=(
                                    f"Suspected unit change {prev_period} → {period}: "
                                    f"ratio≈{ratio:.3g} (near {target:g} or 1/{target:g})."
                                ),
                                details={
                                    "from_period": prev_period.isoformat() if prev_period else None,
                                    "to_period": period.isoformat(),
                                    "from_value": prev_value,
                                    "to_value": value,
                                    "ratio": ratio,
                                    "near_factor": target,
                                },
                            )
                        )
                        break
            prev_value = value
            prev_period = period
    return issues


def check_stale_series(
    store: pd.DataFrame,
    *,
    now: date | datetime | None = None,
    lag_days_by_series: dict[str, int] | None = None,
    grace_days: int = 14,
) -> list[QualityIssue]:
    """Flag series whose latest ref_period should already have been published.

    Inputs: raw store; now clock; typical lags; grace days after expected release.
    Outputs: warning when expected_release + grace < now and no newer period.
    Time allowed to know: now (wall clock or injected); lags; store contents.
             Does not invent new observations.
    """
    if now is None:
        now_ts = pd.Timestamp(datetime.now(UTC)).tz_localize(None)
    elif isinstance(now, datetime):
        ts = pd.Timestamp(now)
        now_ts = ts.tz_convert("UTC").tz_localize(None) if ts.tzinfo is not None else ts
    else:
        now_ts = pd.Timestamp(datetime(now.year, now.month, now.day, 23, 59, 59))

    lags = lag_days_by_series if lag_days_by_series is not None else lag_days_map()
    frame = as_of(normalize_raw_frame(store), now_ts.to_pydatetime())
    issues: list[QualityIssue] = []
    if frame.empty:
        return issues

    for series_id, group in frame.groupby("series_id", sort=True):
        latest_period = max(group["ref_period"])
        lag = lags.get(str(series_id))
        if lag is None:
            # Without a lag prior we cannot judge staleness confidently.
            issues.append(
                QualityIssue(
                    kind=CheckKind.STALE_SERIES,
                    severity=Severity.INFO,
                    series_id=str(series_id),
                    message="No typical lag configured; staleness not assessed.",
                    details={"latest_ref_period": latest_period.isoformat()},
                )
            )
            continue

        # Expect the next month after latest to be published by now?
        # Stale if: month-end(latest) + lag + grace < now AND we would expect
        # a subsequent month — equivalently, expected release of (latest+1 month)
        # is past due. Simpler rule used here: expected release of *latest*
        # itself is fine; series is stale if we are past expected release of the
        # *following* month by grace_days (i.e. a newer print should exist).
        following = _add_months(latest_period, 1)
        expected = end_of_ref_period(following) + timedelta(days=lag)
        expected_ts = pd.Timestamp(datetime(expected.year, expected.month, expected.day, 12, 0, 0))
        due_by = expected_ts + pd.Timedelta(days=grace_days)
        if now_ts > due_by:
            issues.append(
                QualityIssue(
                    kind=CheckKind.STALE_SERIES,
                    severity=Severity.WARNING,
                    series_id=str(series_id),
                    message=(
                        f"Series looks stale: latest ref_period={latest_period}; "
                        f"expected next print by ~{due_by.date()} (lag={lag}d, "
                        f"grace={grace_days}d)."
                    ),
                    details={
                        "latest_ref_period": latest_period.isoformat(),
                        "expected_next_due_by": due_by.isoformat(),
                        "lag_days": lag,
                        "grace_days": grace_days,
                    },
                )
            )
    return issues


def run_all_checks(
    store: pd.DataFrame,
    *,
    as_of_date: date | datetime | None = None,
    now: date | datetime | None = None,
    lag_days_by_series: dict[str, int] | None = None,
    level_break_threshold: float = 0.25,
) -> list[QualityIssue]:
    """Run the full v1 validation suite.

    Inputs: raw store; optional as_of for level/gap checks; now for staleness;
            lag map; level-break threshold.
    Outputs: concatenated QualityIssue list (stable kind order).
    Time allowed to know: as_of_date for historical checks; now for stale check.
    """
    issues: list[QualityIssue] = []
    issues.extend(check_duplicated_rows(store))
    issues.extend(check_missing_periods(store, as_of_date=as_of_date))
    issues.extend(check_unit_changes(store, as_of_date=as_of_date))
    issues.extend(
        check_level_breaks(store, as_of_date=as_of_date, abs_pct_threshold=level_break_threshold)
    )
    issues.extend(
        check_stale_series(store, now=now or as_of_date, lag_days_by_series=lag_days_by_series)
    )
    return issues


def _latest_levels(store: pd.DataFrame, as_of_date: date | datetime | None) -> pd.DataFrame:
    frame = normalize_raw_frame(store)
    if as_of_date is not None:
        return as_of(frame, as_of_date)
    if frame.empty:
        return frame
    ordered = frame.sort_values(
        by=["series_id", "ref_period", "release_timestamp", "retrieved_at"],
        ascending=True,
        kind="mergesort",
    )
    return ordered.drop_duplicates(subset=["series_id", "ref_period"], keep="last")


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _monthly_range(start: date, end: date) -> list[date]:
    start = _month_start(start)
    end = _month_start(end)
    out: list[date] = []
    cur = start
    while cur <= end:
        out.append(cur)
        cur = _add_months(cur, 1)
    return out


def _add_months(value: date, months: int) -> date:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    return date(year, month, 1)


def issues_to_dicts(issues: list[QualityIssue]) -> list[dict[str, Any]]:
    """Serialize issues for JSON/markdown reporting."""
    return [
        {
            "kind": i.kind.value,
            "severity": i.severity.value,
            "series_id": i.series_id,
            "message": i.message,
            "details": i.details,
        }
        for i in issues
    ]
