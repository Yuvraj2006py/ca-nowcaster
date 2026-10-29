"""Generate the series data-quality status report."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from nowcaster.quality.frame import normalize_raw_frame
from nowcaster.quality.types import QualityIssue, SeriesQualityStatus, Severity
from nowcaster.quality.validate import run_all_checks


def summarize_series(
    store: pd.DataFrame,
    issues: list[QualityIssue] | None = None,
    *,
    as_of_date: date | datetime | None = None,
    now: date | datetime | None = None,
) -> list[SeriesQualityStatus]:
    """Build per-series status rows for the quality report.

    Inputs: raw store; optional precomputed issues; clocks for checks.
    Outputs: list of SeriesQualityStatus sorted by series_id.
    Time allowed to know: as_of_date / now passed into checks; store contents.
    """
    frame = normalize_raw_frame(store)
    found = issues if issues is not None else run_all_checks(frame, as_of_date=as_of_date, now=now)

    by_series: dict[str, list[QualityIssue]] = defaultdict(list)
    global_issues: list[QualityIssue] = []
    for issue in found:
        if issue.series_id is None:
            global_issues.append(issue)
        else:
            by_series[issue.series_id].append(issue)

    series_ids = sorted(set(frame["series_id"].astype(str)) | set(by_series))
    rows: list[SeriesQualityStatus] = []
    for series_id in series_ids:
        subset = frame.loc[frame["series_id"] == series_id]
        series_issues = by_series.get(series_id, [])
        n_err = sum(1 for i in series_issues if i.severity == Severity.ERROR)
        n_warn = sum(1 for i in series_issues if i.severity == Severity.WARNING)
        n_info = sum(1 for i in series_issues if i.severity == Severity.INFO)
        # Store-wide issues (e.g. duplicated vintage keys) surface in issue detail;
        # they do not flip every series to fail.
        if subset.empty:
            status = "empty"
        elif n_err:
            status = "fail"
        elif n_warn:
            status = "warn"
        else:
            status = "ok"
        notes_parts = [i.message for i in series_issues[:3]]
        rows.append(
            SeriesQualityStatus(
                series_id=series_id,
                row_count=int(len(subset)),
                ref_period_min=min(subset["ref_period"]).isoformat() if len(subset) else None,
                ref_period_max=max(subset["ref_period"]).isoformat() if len(subset) else None,
                n_errors=n_err,
                n_warnings=n_warn,
                n_info=n_info,
                status=status,
                notes="; ".join(notes_parts) if notes_parts else "No issues flagged.",
            )
        )

    # Expose store-wide findings as a synthetic row so the table is complete.
    if global_issues:
        n_err = sum(1 for i in global_issues if i.severity == Severity.ERROR)
        n_warn = sum(1 for i in global_issues if i.severity == Severity.WARNING)
        n_info = sum(1 for i in global_issues if i.severity == Severity.INFO)
        status = "fail" if n_err else ("warn" if n_warn else "ok")
        rows.insert(
            0,
            SeriesQualityStatus(
                series_id="(store-wide)",
                row_count=int(len(frame)),
                ref_period_min=None,
                ref_period_max=None,
                n_errors=n_err,
                n_warnings=n_warn,
                n_info=n_info,
                status=status,
                notes="; ".join(i.message for i in global_issues[:3]),
            ),
        )
    return rows


def render_quality_report_markdown(
    store: pd.DataFrame,
    *,
    as_of_date: date | datetime | None = None,
    now: date | datetime | None = None,
    title: str = "Data quality status by series",
) -> str:
    """Render a markdown quality report for docs/quality_report.md.

    Inputs: raw store (may be fixture or live); optional clocks.
    Outputs: markdown string.
    Time allowed to know: clocks passed in; store release times already present.
    """
    generated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    frame = normalize_raw_frame(store)
    issues = run_all_checks(frame, as_of_date=as_of_date, now=now)
    statuses = summarize_series(frame, issues, as_of_date=as_of_date, now=now)

    lines: list[str] = [
        f"# {title}",
        "",
        f"Generated: `{generated}` (UTC).",
        "",
        "## Scope",
        "",
        "Owned by **Data Quality and Timing** (`src/nowcaster/quality/`).",
        "Checks: missing periods, unit changes, sudden level breaks, duplicated rows,",
        "stale series. Timing: `as_of(date)` never returns a value with",
        "`release_timestamp` after the cutoff; pseudo-real-time lags are flagged",
        "as approximations when measured vintages are missing.",
        "",
        "## Store snapshot",
        "",
        f"- Raw rows: **{len(frame)}**",
        f"- Distinct series: **{frame['series_id'].nunique() if len(frame) else 0}**",
        f"- Issues found: **{len(issues)}** "
        f"(errors={sum(1 for i in issues if i.severity == Severity.ERROR)}, "
        f"warnings={sum(1 for i in issues if i.severity == Severity.WARNING)}, "
        f"info={sum(1 for i in issues if i.severity == Severity.INFO)})",
        "",
        "## Series status",
        "",
        (
            "| series_id | status | rows | ref_period min | ref_period max "
            "| errors | warnings | notes |"
        ),
        "|---|---|---:|---|---|---:|---:|---|",
    ]

    if not statuses:
        lines.append("| _(none)_ | empty | 0 | — | — | 0 | 0 | No series in store yet. |")
    else:
        for s in statuses:
            note = s.notes.replace("|", "\\|")
            lines.append(
                f"| `{s.series_id}` | {s.status} | {s.row_count} | "
                f"{s.ref_period_min or '—'} | {s.ref_period_max or '—'} | "
                f"{s.n_errors} | {s.n_warnings} | {note} |"
            )

    lines.extend(
        [
            "",
            "## Issue detail",
            "",
        ]
    )
    if not issues:
        lines.append("_No validation issues._")
    else:
        for issue in issues:
            sid = issue.series_id or "(store)"
            lines.append(
                f"- **{issue.severity.value}** / `{issue.kind.value}` / `{sid}`: {issue.message}"
            )

    lines.extend(
        [
            "",
            "## Timing controls",
            "",
            "- `nowcaster.quality.as_of(store, as_of_date)` — latest vintage per",
            "  `(series_id, ref_period)` with `release_timestamp <= as_of_date`.",
            "- `nowcaster.quality.apply_publication_lags(...)` — fills missing",
            "  release times from `typical_lags.yaml` and sets",
            "  `release_is_approximate=true`.",
            "- Phase 1 gate: `tests/gates/test_phase_1.py` asserts no as_of leakage.",
            "",
            "## How this report could be wrong",
            "",
            "- Fixture or incomplete ingest data may not reflect live StatCan/BoC.",
            "- Typical lags are approximations, not official schedules.",
            "- Level-break thresholds can false-flag volatile series (e.g. commodities).",
            "- Staleness needs a configured lag; unknown series_ids are info-only.",
            "",
        ]
    )
    return "\n".join(lines)


def write_quality_report(
    store: pd.DataFrame,
    path: Path,
    *,
    as_of_date: date | datetime | None = None,
    now: date | datetime | None = None,
) -> Path:
    """Write the markdown quality report to path.

    Inputs: raw store; destination path; optional clocks.
    Outputs: path written.
    Time allowed to know: same as render_quality_report_markdown.
    """
    text = render_quality_report_markdown(store, as_of_date=as_of_date, now=now)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
