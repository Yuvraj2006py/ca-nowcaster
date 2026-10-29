"""Shared types for data-quality findings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CheckKind(str, Enum):
    """Validation check categories owned by the quality package."""

    MISSING_PERIODS = "missing_periods"
    UNIT_CHANGE = "unit_change"
    LEVEL_BREAK = "level_break"
    DUPLICATED_ROWS = "duplicated_rows"
    STALE_SERIES = "stale_series"


class Severity(str, Enum):
    """How urgently a finding should block downstream use."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class QualityIssue:
    """One validation finding for a series (or the whole store).

    Inputs: check outputs from validate.run_all_checks.
    Outputs: immutable issue used in reports and tests.
    Time allowed to know: only the as_of / now clocks passed into the check.
    """

    kind: CheckKind
    severity: Severity
    series_id: str | None
    message: str
    details: dict[str, Any]


@dataclass(frozen=True)
class SeriesQualityStatus:
    """Roll-up status for one series_id in the quality report.

    Inputs: issues + coverage stats for a single series.
    Outputs: row in docs/quality_report.md.
    Time allowed to know: report generation clock only; no future releases.
    """

    series_id: str
    row_count: int
    ref_period_min: str | None
    ref_period_max: str | None
    n_errors: int
    n_warnings: int
    n_info: int
    status: str  # "ok" | "warn" | "fail" | "empty"
    notes: str
