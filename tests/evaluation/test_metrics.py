"""Unit tests for metric scaffolding."""

from __future__ import annotations

import numpy as np

from nowcaster.evaluation.metrics import (
    classifier_metrics_stub,
    compute_regression_metrics,
    directional_accuracy,
    interval_coverage,
    mae,
    ratio_vs_baseline,
    rmse,
)


def test_rmse_mae_basic() -> None:
    actual = [0.0, 1.0, 2.0]
    pred = [0.0, 1.0, 4.0]
    assert rmse(actual, pred) == np.sqrt((0 + 0 + 4) / 3)
    assert mae(actual, pred) == (0 + 0 + 2) / 3


def test_directional_accuracy_on_growth_signs() -> None:
    actual = [0.5, -0.2, 0.1]
    pred = [0.1, -0.9, -0.1]
    # Two of three signs match.
    assert directional_accuracy(actual, pred) == 2.0 / 3.0


def test_interval_coverage() -> None:
    actual = [0.0, 1.0, 2.0]
    lower = [-1.0, 0.5, 1.5]
    upper = [1.0, 1.5, 1.9]
    # first two inside, third outside
    assert interval_coverage(actual, lower, upper) == 2.0 / 3.0


def test_compute_regression_metrics_and_ratio() -> None:
    actual = [0.0, 1.0, 2.0, 3.0]
    cand = [0.1, 1.1, 2.1, 2.9]
    base = [0.0, 0.0, 0.0, 0.0]
    c_m = compute_regression_metrics(
        actual,
        cand,
        lower_80=[-1, 0, 1, 2],
        upper_80=[1, 2, 3, 4],
        lower_95=[-2, -1, 0, 1],
        upper_95=[2, 3, 4, 5],
    )
    b_m = compute_regression_metrics(actual, base)
    rel = ratio_vs_baseline(c_m, b_m, "last_value")
    assert rel.baseline_name == "last_value"
    assert rel.rmse_ratio < 1.0
    assert rel.mae_ratio < 1.0
    assert c_m.coverage_80 == 1.0
    assert c_m.n == 4


def test_classifier_stub_unavailable() -> None:
    stub = classifier_metrics_stub()
    assert stub.available is False
    assert stub.accuracy is None
    assert "Phase 3" in stub.note
