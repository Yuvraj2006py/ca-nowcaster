"""Walk-forward harness, COVID variants, and holdout lock tests."""

from __future__ import annotations

from datetime import date

import pytest

from nowcaster.evaluation.covid import DEFAULT_COVID_SHOCK_MONTHS, is_covid_shock_month
from nowcaster.evaluation.holdout_lock import (
    HOLDOUT_MONTHS,
    HoldoutLockedError,
    resolve_holdout_window,
)
from nowcaster.evaluation.walk_forward import (
    WalkForwardConfig,
    compare_to_baselines,
    run_baseline_suite,
    run_walk_forward,
)
from tests.evaluation.baseline_doubles import LastValueBaseline, RollingMeanBaseline


def test_covid_defaults_include_spring_2020() -> None:
    assert is_covid_shock_month(date(2020, 4, 1))
    assert date(2020, 4, 1) in DEFAULT_COVID_SHOCK_MONTHS
    assert not is_covid_shock_month(date(2019, 4, 1))


def test_holdout_window_reserves_final_24(synthetic_panel) -> None:
    X, _y, _as_of = synthetic_panel
    months = list(X.index)
    window = resolve_holdout_window(months)
    assert window.n_holdout == HOLDOUT_MONTHS
    assert window.holdout_months[0] == date(2021, 1, 1)
    assert window.holdout_months[-1] == date(2022, 12, 1)
    assert date(2022, 12, 1) not in window.train_eval_months


def test_walk_forward_skips_holdout_and_reports_covid_variants(synthetic_panel) -> None:
    X, y, as_of = synthetic_panel
    cfg = WalkForwardConfig(min_train_months=12, exclude_holdout=True)
    result = run_walk_forward(LastValueBaseline, X, y, as_of_by_month=as_of, config=cfg)
    assert result.folds
    assert all(not f.is_holdout for f in result.folds)
    assert result.metrics.full_sample.n >= result.metrics.headline.n
    # At least one COVID fold exists in the eval window when min_train is 12.
    assert any(f.is_covid_shock for f in result.folds)
    assert result.metrics.headline.n == sum(1 for f in result.folds if not f.is_covid_shock)
    assert result.metrics.classifier["available"] is False


def test_holdout_unlock_required_to_score(synthetic_panel) -> None:
    X, y, as_of = synthetic_panel
    cfg = WalkForwardConfig(
        min_train_months=12,
        exclude_holdout=False,
        holdout_unlocked=False,
    )
    with pytest.raises(HoldoutLockedError):
        run_walk_forward(LastValueBaseline, X, y, as_of_by_month=as_of, config=cfg)


def test_baseline_suite_and_ratios(synthetic_panel) -> None:
    X, y, as_of = synthetic_panel
    cfg = WalkForwardConfig(min_train_months=12)
    factories = {
        "last_value": LastValueBaseline,
        "rolling_mean": RollingMeanBaseline,
    }
    results = run_baseline_suite(factories, X, y, as_of_by_month=as_of, config=cfg)
    assert set(results) == {"last_value", "rolling_mean"}
    compared = compare_to_baselines(results["rolling_mean"], {"last_value": results["last_value"]})
    assert len(compared.metrics.vs_baselines_headline) == 1
    assert compared.metrics.vs_baselines_headline[0].baseline_name == "last_value"
    assert compared.metrics.vs_baselines_headline[0].rmse_ratio > 0
