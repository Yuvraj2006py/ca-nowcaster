"""Prediction-interval helpers shared by Phase 2 baselines.

Inputs: point forecasts and residual scale estimated on the training window.
Outputs: PredictionIntervals at nominal 80% and 95% coverage.
Time allowed to know: training residuals only; no future actuals.
"""

from __future__ import annotations

import math

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
