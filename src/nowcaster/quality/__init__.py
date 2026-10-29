"""Data quality checks and as-of / release-calendar views.

Public API for Role 2 (Data Quality and Timing). Consumes the raw-store
schema from nowcaster.contracts only — does not import ingest internals.
"""

from nowcaster.quality.pseudo_realtime import (
    apply_publication_lags,
    approximate_release_timestamp,
    ensure_release_timestamps,
)
from nowcaster.quality.release_calendar import (
    as_of,
    assert_no_as_of_leakage,
    earliest_release,
    release_calendar,
)
from nowcaster.quality.report import (
    render_quality_report_markdown,
    summarize_series,
    write_quality_report,
)
from nowcaster.quality.types import CheckKind, QualityIssue, SeriesQualityStatus, Severity
from nowcaster.quality.validate import (
    check_duplicated_rows,
    check_level_breaks,
    check_missing_periods,
    check_stale_series,
    check_unit_changes,
    run_all_checks,
)

__all__ = [
    "CheckKind",
    "QualityIssue",
    "SeriesQualityStatus",
    "Severity",
    "apply_publication_lags",
    "approximate_release_timestamp",
    "as_of",
    "assert_no_as_of_leakage",
    "check_duplicated_rows",
    "check_level_breaks",
    "check_missing_periods",
    "check_stale_series",
    "check_unit_changes",
    "earliest_release",
    "ensure_release_timestamps",
    "release_calendar",
    "render_quality_report_markdown",
    "run_all_checks",
    "summarize_series",
    "write_quality_report",
]
