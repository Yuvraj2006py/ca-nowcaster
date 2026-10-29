"""Prediction-interval helpers for baselines and Phase 3 candidates.

Inputs: point forecasts and residual scale / absolute residuals from the
training (or train-calibration) window.
Outputs: PredictionIntervals at nominal 80% and 95% coverage.
Time allowed to know: training residuals only; no future actuals.
"""

from __future__ import annotations

import math

import numpy as np

from nowcaster.contracts import PredictionIntervals

# Standard normal critical values for central prediction intervals.
# P(|Z| <= z) = 0.80 => z = Φ^{-1}(0.90); P(|Z| <= z) = 0.95 => Φ^{-1}(0.975).
Z_80 = 1.2815515655446004
Z_95 = 1.959963984540054

# Floor so degenerate in-sample fits do not emit zero-width intervals.
_MIN_SCALE = 1e-8


def gaussian_intervals(point: float, residual_std: float) -> PredictionIntervals:
    """Build symmetric 80%/95% intervals from a Gaussian residual assumption.

    Inputs: point forecast; residual_std estimated from one-step training errors.
    Outputs: PredictionIntervals around point.
    Time allowed to know: residual_std from fit window only.
    """
    if not math.isfinite(point):
        raise ValueError(f"point forecast must be finite, got {point!r}")
    if not math.isfinite(residual_std) or residual_std < 0:
        raise ValueError(f"residual_std must be finite and >= 0, got {residual_std!r}")

    scale = max(float(residual_std), _MIN_SCALE)
    return PredictionIntervals(
        point=float(point),
        lower_80=float(point - Z_80 * scale),
        upper_80=float(point + Z_80 * scale),
        lower_95=float(point - Z_95 * scale),
        upper_95=float(point + Z_95 * scale),
    )


def conformal_quantile(abs_residuals: np.ndarray, level: float) -> float:
    """Split-conformal absolute-residual quantile for nominal coverage ``level``.

    Inputs: absolute residuals on a calibration slice of the training window;
            level in (0, 1) e.g. 0.80 or 0.95.
    Outputs: non-negative half-width (finite; floored at _MIN_SCALE).
    Time allowed to know: calibration residuals from the fit window only.
    """
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must be in (0, 1), got {level!r}")
    residuals = np.asarray(abs_residuals, dtype=np.float64).reshape(-1)
    residuals = residuals[np.isfinite(residuals)]
    if residuals.size == 0:
        return _MIN_SCALE
    # Finite-sample correction: q = ceil((n+1)*level) / n style index.
    n = residuals.size
    rank = int(math.ceil((n + 1) * level))
    rank = min(max(rank, 1), n)
    ordered = np.sort(residuals)
    return max(float(ordered[rank - 1]), _MIN_SCALE)


def conformal_intervals(point: float, abs_residuals: np.ndarray) -> PredictionIntervals:
    """Symmetric 80%/95% intervals via split conformal absolute residuals.

    Inputs: point forecast; absolute residuals from a training calibration fold.
    Outputs: PredictionIntervals around point (tree-friendly; no Gaussian assumption).
    Time allowed to know: calibration residuals from the fit window only.
    """
    if not math.isfinite(point):
        raise ValueError(f"point forecast must be finite, got {point!r}")
    half_80 = conformal_quantile(abs_residuals, 0.80)
    half_95 = conformal_quantile(abs_residuals, 0.95)
    # Ensure nesting even with tiny calibration sets.
    half_95 = max(half_95, half_80)
    return PredictionIntervals(
        point=float(point),
        lower_80=float(point - half_80),
        upper_80=float(point + half_80),
        lower_95=float(point - half_95),
        upper_95=float(point + half_95),
    )


def clip_unit_interval(intervals: PredictionIntervals) -> PredictionIntervals:
    """Clip probability intervals to [0, 1] while preserving nesting and point.

    Inputs: PredictionIntervals whose point is a probability in [0, 1].
    Outputs: clipped PredictionIntervals.
    Time allowed to know: none beyond the supplied intervals.
    """
    point = min(1.0, max(0.0, float(intervals.point)))
    lower_95 = min(point, max(0.0, float(intervals.lower_95)))
    lower_80 = min(point, max(lower_95, float(intervals.lower_80)))
    upper_80 = max(point, min(1.0, float(intervals.upper_80)))
    upper_95 = max(upper_80, min(1.0, float(intervals.upper_95)))
    return PredictionIntervals(
        point=point,
        lower_80=lower_80,
        upper_80=upper_80,
        lower_95=lower_95,
        upper_95=upper_95,
    )
