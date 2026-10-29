"""Point, interval, directional, and classifier metric scaffolding.

Phase 2: RMSE/MAE vs baselines (ratios), directional accuracy, interval
coverage. Classifier hooks stubbed for Phase 3. Full model verdicts and
Diebold-Mariano / bootstrap CIs land in Phase 3 evaluation_report.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class RegressionMetrics:
    """Point-forecast metrics for one prediction stream.

    Inputs: aligned actuals and point predictions (and optional intervals).
    Outputs: RMSE, MAE, directional accuracy, interval coverage rates.
    Time allowed to know: actuals only after their release; callers enforce that.
    """

    n: int
    rmse: float
    mae: float
    directional_accuracy: float | None
    coverage_80: float | None
    coverage_95: float | None


@dataclass(frozen=True)
class BaselineRelativeMetrics:
    """Candidate metrics plus ratios vs a named baseline (candidate / baseline).

    Ratio < 1 means the candidate has lower error than the baseline.
    """

    baseline_name: str
    candidate: RegressionMetrics
    baseline: RegressionMetrics
    rmse_ratio: float
    mae_ratio: float


@dataclass(frozen=True)
class MetricBundle:
    """Headline (COVID-excluded) and full-sample metric views.

    Both versions are always reported; headline is the primary comparison surface.
    """

    headline: RegressionMetrics  # COVID shock months excluded
    full_sample: RegressionMetrics
    vs_baselines_headline: tuple[BaselineRelativeMetrics, ...] = ()
    vs_baselines_full: tuple[BaselineRelativeMetrics, ...] = ()
    classifier: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ClassifierMetricsStub:
    """Placeholder for Phase 3 binary direction-classifier metrics.

    Inputs: none in Phase 2 (stub only).
    Outputs: empty structure documenting expected Phase 3 fields.
    Time allowed to know: n/a until Phase 3 wires real labels/predictions.
    """

    available: bool = False
    note: str = (
        "Classifier metrics (accuracy, precision, recall, confusion matrix) "
        "are stubbed in Phase 2; Phase 3 evaluation_report.md will fill them."
    )
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    confusion_matrix: list[list[int]] | None = None


def _as_float_array(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"expected 1-d array, got shape {arr.shape}")
    return arr


def rmse(actual: Any, predicted: Any) -> float:
    """Root mean squared error.

    Inputs: aligned actual and predicted arrays.
    Outputs: float RMSE (nan if empty).
    Time allowed to know: caller-supplied actuals only.
    """
    a = _as_float_array(actual)
    p = _as_float_array(predicted)
    if a.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean((p - a) ** 2)))


def mae(actual: Any, predicted: Any) -> float:
    """Mean absolute error.

    Inputs: aligned actual and predicted arrays.
    Outputs: float MAE (nan if empty).
    Time allowed to know: caller-supplied actuals only.
    """
    a = _as_float_array(actual)
    p = _as_float_array(predicted)
    if a.size == 0:
        return float("nan")
    return float(np.mean(np.abs(p - a)))


def directional_accuracy(
    actual: Any,
    predicted: Any,
    *,
    previous_actual: Any | None = None,
) -> float | None:
    """Share of months where predicted direction of change matches actual.

    If previous_actual is provided, direction is sign(value - previous).
    Otherwise direction is sign of the level itself (useful for MoM growth
    series already expressed as changes: sign(actual) vs sign(predicted)).

    Inputs: aligned actuals/predictions; optional lag-1 actuals for deltas.
    Outputs: fraction in [0, 1], or None if undefined (n < 1 or all zeros).
    Time allowed to know: caller-supplied actuals only.
    """
    a = _as_float_array(actual)
    p = _as_float_array(predicted)
    if a.size == 0:
        return None
    if previous_actual is not None:
        prev = _as_float_array(previous_actual)
        if prev.size != a.size:
            raise ValueError("previous_actual length must match actual")
        a_dir = np.sign(a - prev)
        p_dir = np.sign(p - prev)
    else:
        a_dir = np.sign(a)
        p_dir = np.sign(p)
    # Treat exact zeros as a defined direction class (flat).
    correct = a_dir == p_dir
    return float(np.mean(correct))


def interval_coverage(
    actual: Any,
    lower: Any,
    upper: Any,
) -> float | None:
    """Fraction of actuals falling inside [lower, upper] inclusive.

    Inputs: aligned actuals and interval bounds.
    Outputs: coverage rate, or None if empty.
    Time allowed to know: caller-supplied actuals only.
    """
    a = _as_float_array(actual)
    lo = _as_float_array(lower)
    hi = _as_float_array(upper)
    if a.size == 0:
        return None
    inside = (a >= lo) & (a <= hi)
    return float(np.mean(inside))


def compute_regression_metrics(
    actual: Any,
    predicted: Any,
    *,
    lower_80: Any | None = None,
    upper_80: Any | None = None,
    lower_95: Any | None = None,
    upper_95: Any | None = None,
    previous_actual: Any | None = None,
) -> RegressionMetrics:
    """Aggregate point/interval/direction metrics for one aligned sample.

    Inputs: actuals, point preds, optional interval bounds and lag-1 actuals.
    Outputs: RegressionMetrics.
    Time allowed to know: caller-supplied actuals only.
    """
    a = _as_float_array(actual)
    p = _as_float_array(predicted)
    if a.size != p.size:
        raise ValueError("actual and predicted must have equal length")
    cov80 = (
        interval_coverage(a, lower_80, upper_80)
        if lower_80 is not None and upper_80 is not None
        else None
    )
    cov95 = (
        interval_coverage(a, lower_95, upper_95)
        if lower_95 is not None and upper_95 is not None
        else None
    )
    return RegressionMetrics(
        n=int(a.size),
        rmse=rmse(a, p),
        mae=mae(a, p),
        directional_accuracy=directional_accuracy(a, p, previous_actual=previous_actual),
        coverage_80=cov80,
        coverage_95=cov95,
    )


def ratio_vs_baseline(
    candidate: RegressionMetrics,
    baseline: RegressionMetrics,
    baseline_name: str,
) -> BaselineRelativeMetrics:
    """RMSE/MAE ratios of candidate vs baseline (candidate / baseline).

    Inputs: precomputed metrics for candidate and baseline.
    Outputs: BaselineRelativeMetrics; ratios are nan if baseline error is 0.
    Time allowed to know: n/a (operates on summary stats only).
    """

    def _ratio(num: float, den: float) -> float:
        if den == 0.0 or np.isnan(den) or np.isnan(num):
            return float("nan")
        return float(num / den)

    return BaselineRelativeMetrics(
        baseline_name=baseline_name,
        candidate=candidate,
        baseline=baseline,
        rmse_ratio=_ratio(candidate.rmse, baseline.rmse),
        mae_ratio=_ratio(candidate.mae, baseline.mae),
    )


def classifier_metrics_stub() -> ClassifierMetricsStub:
    """Return Phase 2 stub for classifier metrics.

    Inputs: none.
    Outputs: ClassifierMetricsStub marking metrics unavailable until Phase 3.
    Time allowed to know: n/a.
    """
    return ClassifierMetricsStub()
