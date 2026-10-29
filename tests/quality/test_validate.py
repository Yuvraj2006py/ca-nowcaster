"""Validation check unit tests."""

from __future__ import annotations

from datetime import date

import pandas as pd

from nowcaster.quality import (
    CheckKind,
    check_duplicated_rows,
    check_level_breaks,
    check_missing_periods,
    check_stale_series,
    check_unit_changes,
    run_all_checks,
)


def test_missing_periods_detects_gap(quality_fixture_store: pd.DataFrame) -> None:
    issues = check_missing_periods(quality_fixture_store)
    gap = [i for i in issues if i.kind == CheckKind.MISSING_PERIODS]
    assert any(i.series_id == "fixture_gap_series" for i in gap)
    clean = [i for i in gap if i.series_id == "fixture_clean_index"]
    assert clean == []


def test_unit_change_detects_1000x(quality_fixture_store: pd.DataFrame) -> None:
    issues = check_unit_changes(quality_fixture_store)
    assert any(
        i.kind == CheckKind.UNIT_CHANGE and i.series_id == "fixture_unit_change" for i in issues
    )


def test_duplicated_rows(quality_fixture_store: pd.DataFrame) -> None:
    issues = check_duplicated_rows(quality_fixture_store)
    assert any(i.kind == CheckKind.DUPLICATED_ROWS for i in issues)


def test_level_breaks_on_unit_jump(quality_fixture_store: pd.DataFrame) -> None:
    issues = check_level_breaks(quality_fixture_store, abs_pct_threshold=0.25)
    assert any(i.series_id == "fixture_unit_change" for i in issues)


def test_stale_series_with_lag(quality_fixture_store: pd.DataFrame) -> None:
    issues = check_stale_series(
        quality_fixture_store,
        now=date(2024, 6, 1),
        lag_days_by_series={"ca_gdp_basic_prices": 60},
        grace_days=14,
    )
    assert any(
        i.kind == CheckKind.STALE_SERIES and i.series_id == "ca_gdp_basic_prices" for i in issues
    )


def test_run_all_checks_returns_mixed_kinds(quality_fixture_store: pd.DataFrame) -> None:
    issues = run_all_checks(quality_fixture_store, now=date(2024, 6, 1))
    kinds = {i.kind for i in issues}
    assert CheckKind.MISSING_PERIODS in kinds
    assert CheckKind.DUPLICATED_ROWS in kinds
    assert CheckKind.UNIT_CHANGE in kinds
