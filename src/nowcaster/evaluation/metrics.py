"""Point, interval, directional, and classifier metrics.

Phase 3: RMSE/MAE vs baselines (ratios), directional accuracy, interval
coverage, binary classifier metrics (confusion / precision / recall / F1),
and calibration reliability bins for probability forecasts.
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
class CalibrationBin:
    """One reliability-diagram bin for probability forecasts.

    Inputs: predictions falling in [lower, upper).
    Outputs: mean predicted probability and empirical positive rate.
    Time allowed to know: labels only after release.
    """

    lower: float
    upper: float
    n: int
    mean_predicted: float
    fraction_positive: float


@dataclass(frozen=True)
class ClassifierMetrics:
    """Binary direction-classifier metrics (beat previous month: yes/no).

    Inputs: aligned true labels and predicted labels / probabilities.
    Outputs: confusion matrix, precision, recall, F1, accuracy, calibration bins.
    Time allowed to know: labels only after their release.
    """

    available: bool
    n: int
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    # [[TN, FP], [FN, TP]] in sklearn convention for labels {0,1}
    confusion_matrix: tuple[tuple[int, int], tuple[int, int]] | None
    calibration_bins: tuple[CalibrationBin, ...] = ()
    note: str = ""


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


# Back-compat alias used by Phase 2 exports / tests.
ClassifierMetricsStub = ClassifierMetrics


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


def _binary_labels(values: Any) -> np.ndarray:
    arr = np.asarray(values)
    if arr.dtype == bool:
        return arr.astype(int)
    out = np.asarray(arr, dtype=float)
    # Map {0,1} or {-1,1}/sign to {0,1}; positives (>0) -> 1.
    return (out > 0).astype(int)


def calibration_reliability(
    y_true: Any,
    y_prob: Any,
    *,
    n_bins: int = 10,
) -> tuple[CalibrationBin, ...]:
    """Reliability-diagram bins for probability forecasts of the positive class.

    Inputs: binary labels; predicted probabilities in [0, 1]; bin count.
    Outputs: tuple of CalibrationBin (empty bins omitted).
    Time allowed to know: caller-supplied labels only.
    """
    labels = _binary_labels(y_true)
    probs = _as_float_array(y_prob)
    if labels.size != probs.size:
        raise ValueError("y_true and y_prob must have equal length")
    if labels.size == 0:
        return ()
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins: list[CalibrationBin] = []
    for i in range(n_bins):
        lo = float(edges[i])
        hi = float(edges[i + 1])
        if i == n_bins - 1:
            mask = (probs >= lo) & (probs <= hi)
        else:
            mask = (probs >= lo) & (probs < hi)
        count = int(np.sum(mask))
        if count == 0:
            continue
        bins.append(
            CalibrationBin(
                lower=lo,
                upper=hi,
                n=count,
                mean_predicted=float(np.mean(probs[mask])),
                fraction_positive=float(np.mean(labels[mask])),
            )
        )
    return tuple(bins)


def compute_classifier_metrics(
    y_true: Any,
    y_pred: Any,
    *,
    y_prob: Any | None = None,
    n_calibration_bins: int = 10,
) -> ClassifierMetrics:
    """Confusion matrix, precision, recall, F1, accuracy, optional calibration.

    Positive class = 1 (growth beat previous month / positive MoM direction).

    Inputs: true labels; predicted hard labels; optional probabilities for
      calibration; bin count for reliability diagram.
    Outputs: ClassifierMetrics.
    Time allowed to know: caller-supplied labels only.
    """
    truth = _binary_labels(y_true)
    pred = _binary_labels(y_pred)
    if truth.size != pred.size:
        raise ValueError("y_true and y_pred must have equal length")
    if truth.size == 0:
        return ClassifierMetrics(
            available=False,
            n=0,
            accuracy=None,
            precision=None,
            recall=None,
            f1=None,
            confusion_matrix=None,
            note="no classifier observations",
        )

    tn = int(np.sum((truth == 0) & (pred == 0)))
    fp = int(np.sum((truth == 0) & (pred == 1)))
    fn = int(np.sum((truth == 1) & (pred == 0)))
    tp = int(np.sum((truth == 1) & (pred == 1)))
    accuracy = float((tp + tn) / truth.size)
    precision = float(tp / (tp + fp)) if (tp + fp) else None
    recall = float(tp / (tp + fn)) if (tp + fn) else None
    if precision is None or recall is None or (precision + recall) == 0:
        f1 = None
    else:
        f1 = float(2 * precision * recall / (precision + recall))

    cal: tuple[CalibrationBin, ...] = ()
    if y_prob is not None:
        cal = calibration_reliability(truth, y_prob, n_bins=n_calibration_bins)

    return ClassifierMetrics(
        available=True,
        n=int(truth.size),
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        confusion_matrix=((tn, fp), (fn, tp)),
        calibration_bins=cal,
        note="",
    )


def classifier_metrics_to_dict(metrics: ClassifierMetrics) -> dict[str, Any]:
    """Serialize ClassifierMetrics for MetricBundle.classifier storage.

    Inputs: ClassifierMetrics.
    Outputs: JSON-friendly dict.
    Time allowed to know: n/a.
    """
    cm = metrics.confusion_matrix
    return {
        "available": metrics.available,
        "n": metrics.n,
        "accuracy": metrics.accuracy,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "confusion_matrix": [list(cm[0]), list(cm[1])] if cm is not None else None,
        "calibration_bins": [
            {
                "lower": b.lower,
                "upper": b.upper,
                "n": b.n,
                "mean_predicted": b.mean_predicted,
                "fraction_positive": b.fraction_positive,
            }
            for b in metrics.calibration_bins
        ],
        "note": metrics.note,
    }


def classifier_metrics_stub() -> ClassifierMetrics:
    """Return empty classifier metrics when no direction model is registered.

    Inputs: none.
    Outputs: ClassifierMetrics with available=False.
    Time allowed to know: n/a.
    """
    return ClassifierMetrics(
        available=False,
        n=0,
        accuracy=None,
        precision=None,
        recall=None,
        f1=None,
        confusion_matrix=None,
        note=(
            "No Phase 3 direction classifier registered yet; "
            "sign(point) directional accuracy is reported on the regression side."
        ),
    )


def direction_labels_from_growth(growth: Any) -> np.ndarray:
    """Map MoM growth to binary 'beat previous' labels via sign > 0.

    For growth already expressed as MoM change, positive growth = beat flat/zero
    previous (secondary target approximation when lag-1 comparison is unavailable).

    Inputs: MoM growth values.
    Outputs: 0/1 int array.
    Time allowed to know: caller-supplied growth only.
    """
    return _binary_labels(growth)


def calibration_svg(
    bins: tuple[CalibrationBin, ...],
    *,
    width: int = 420,
    height: int = 320,
) -> str:
    """Render a simple reliability diagram as SVG (no plotting dependency).

    Inputs: calibration bins from compute_classifier_metrics.
    Outputs: SVG string.
    Time allowed to know: n/a (summary bins only).
    """
    pad_l, pad_r, pad_t, pad_b = 48, 20, 20, 48
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    def xy(px: float, py: float) -> tuple[float, float]:
        return pad_l + px * plot_w, pad_t + (1.0 - py) * plot_h

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fafafa"/>',
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" '
        'stroke="#333" stroke-width="1"/>',
        f'<line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" '
        f'y2="{pad_t + plot_h}" stroke="#333" stroke-width="1"/>',
    ]
    # Diagonal perfect-calibration line.
    x0, y0 = xy(0.0, 0.0)
    x1, y1 = xy(1.0, 1.0)
    parts.append(
        f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y1}" '
        'stroke="#999" stroke-dasharray="4 3" stroke-width="1"/>'
    )
    # Points + connecting polyline.
    if bins:
        coords: list[str] = []
        for b in bins:
            px, py = xy(b.mean_predicted, b.fraction_positive)
            coords.append(f"{px},{py}")
            r = 3 + min(b.n, 20) * 0.15
            parts.append(
                f'<circle cx="{px}" cy="{py}" r="{r}" fill="#1f4e79" fill-opacity="0.85"/>'
            )
        parts.append(
            f'<polyline points="{" ".join(coords)}" fill="none" '
            'stroke="#1f4e79" stroke-width="1.5"/>'
        )
    parts.append(
        f'<text x="{pad_l + plot_w / 2}" y="{height - 12}" text-anchor="middle" '
        'font-size="12" fill="#333">Mean predicted probability</text>'
    )
    parts.append(
        f'<text x="14" y="{pad_t + plot_h / 2}" text-anchor="middle" '
        f'font-size="12" fill="#333" '
        f'transform="rotate(-90 14 {pad_t + plot_h / 2})">Fraction positive</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)
