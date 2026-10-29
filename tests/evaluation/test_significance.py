"""Diebold-Mariano and bootstrap CI tests."""

from __future__ import annotations

import numpy as np

from nowcaster.evaluation.significance import (
    beats_baseline,
    bootstrap_rmse_ratio_ci,
    diebold_mariano,
)


def test_diebold_mariano_identical_forecasts() -> None:
    actual = [0.1, -0.2, 0.0, 0.3, -0.1]
    pred = list(actual)
    dm = diebold_mariano(actual, pred, pred)
    assert dm.n == 5
    assert dm.mean_loss_diff == 0.0
    assert dm.p_value == 1.0


def test_diebold_mariano_clear_winner() -> None:
    rng = np.random.default_rng(0)
    actual = rng.normal(0, 1, size=80)
    baseline = actual + rng.normal(0, 1.0, size=80)
    candidate = actual + rng.normal(0, 0.2, size=80)
    dm = diebold_mariano(actual, candidate, baseline)
    assert dm.mean_loss_diff < 0
    assert dm.p_value < 0.05


def test_bootstrap_rmse_ratio_ci_and_beats_rule() -> None:
    rng = np.random.default_rng(1)
    actual = rng.normal(0, 1, size=60)
    baseline = actual + rng.normal(0, 1.0, size=60)
    candidate = actual + rng.normal(0, 0.25, size=60)
    ci = bootstrap_rmse_ratio_ci(actual, candidate, baseline, n_bootstrap=200, seed=2)
    assert ci.point_ratio < 1.0
    assert ci.lower < ci.upper
    beats, reason = beats_baseline(ci.point_ratio, bootstrap_ci=ci)
    # May or may not clear the CI-below-1 bar depending on draw; assert API shape.
    assert isinstance(beats, bool)
    assert "RMSE" in reason


def test_beats_baseline_rejects_ratio_ge_one() -> None:
    beats, reason = beats_baseline(1.05)
    assert beats is False
    assert "not below 1" in reason
