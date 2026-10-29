"""Phase 2 nowcast baselines: last value, AR(1), and rolling mean.

These models intentionally ignore feature columns in X. They use only the
target history y at fit time, and the row count of X at predict time, so the
evaluation harness can call them through the shared NowcastModel interface
without model-side changes when features evolve.

Inputs: X (row scaffold), y (MoM growth history available at the fit origin).
Outputs: ModelPrediction with point forecasts and 80%/95% intervals.
Time allowed to know: only training y passed to fit; no future actuals.
"""

from __future__ import annotations

from typing import Any, Self

import numpy as np

from nowcaster.contracts import ModelPrediction, PredictionIntervals
from nowcaster.models._array import n_rows, require_finite_1d, residual_std, to_1d_float
from nowcaster.models.intervals import gaussian_intervals


class LastValueBaseline:
    """Naive baseline: forecast equals the last observed target value.

    Point: y_T for every requested row.
    Intervals: Gaussian around the point using the std of first differences
    on the training window (one-step last-value errors).
    """

    name: str = "last_value"
    version: str = "0.1.0"

    def __init__(self) -> None:
        self._fitted: bool = False
        self._last_value: float | None = None
        self._residual_std: float = 0.0

    def fit(self, X: Any, y: Any) -> Self:
        """Fit last-value baseline on target history y.

        Inputs: X (ignored except for interface parity); y (ordered MoM growth).
        Outputs: self (fitted).
        Time allowed to know: y observations in the training window only.
        """
        del X  # baselines do not use features
        series = require_finite_1d(to_1d_float(y), name="y", min_len=1)
        self._last_value = float(series[-1])
        if series.size >= 2:
            residuals = series[1:] - series[:-1]
            self._residual_std = residual_std(residuals)
        else:
            self._residual_std = 0.0
        self._fitted = True
        return self

    def predict(self, X: Any) -> ModelPrediction:
        """Predict last training value for each row of X.

        Inputs: X with one row per period to score (feature values unused).
        Outputs: ModelPrediction aligned to rows of X.
        Time allowed to know: fitted last value and residual scale only.
        """
        self._require_fitted()
        assert self._last_value is not None
        count = n_rows(X)
        if count < 1:
            return ModelPrediction(
                points=np.asarray([], dtype=np.float64),
                intervals=[],
                model_name=self.name,
                model_version=self.version,
            )

        point = self._last_value
        points = np.full(count, point, dtype=np.float64)
        intervals = [gaussian_intervals(point, self._residual_std) for _ in range(count)]
        return ModelPrediction(
            points=points,
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(f"{self.name} must be fit() before predict()")


class AR1Baseline:
    """AR(1) baseline: y_t = c + φ y_{t-1} + ε_t fitted by OLS on training y.

    Multi-row predict chains one-step forecasts from the last training value
    (no future actuals). Intervals use the in-sample one-step residual std.
    """

    name: str = "ar1"
    version: str = "0.1.0"

    def __init__(self) -> None:
        self._fitted: bool = False
        self._intercept: float = 0.0
        self._phi: float = 0.0
        self._last_value: float | None = None
        self._residual_std: float = 0.0

    def fit(self, X: Any, y: Any) -> Self:
        """Fit AR(1) coefficients on target history y.

        Inputs: X (ignored); y with at least two finite observations.
        Outputs: self (fitted).
        Time allowed to know: y in the training window only.
        """
        del X
        series = require_finite_1d(to_1d_float(y), name="y", min_len=2)
        lagged = series[:-1]
        current = series[1:]
        design = np.column_stack([np.ones(lagged.size, dtype=np.float64), lagged])
        coef, _, _, _ = np.linalg.lstsq(design, current, rcond=None)
        self._intercept = float(coef[0])
        self._phi = float(coef[1])
        fitted = design @ coef
        self._residual_std = residual_std(current - fitted)
        self._last_value = float(series[-1])
        self._fitted = True
        return self

    def predict(self, X: Any) -> ModelPrediction:
        """Chain AR(1) forecasts for each row of X from the training end.

        Inputs: X with one row per forward step (features unused).
        Outputs: ModelPrediction with chained points and Gaussian intervals.
        Time allowed to know: fitted coefficients and last training y only.
        """
        self._require_fitted()
        assert self._last_value is not None
        count = n_rows(X)
        if count < 1:
            return ModelPrediction(
                points=np.asarray([], dtype=np.float64),
                intervals=[],
                model_name=self.name,
                model_version=self.version,
            )

        points = np.empty(count, dtype=np.float64)
        intervals: list[PredictionIntervals] = []
        prev = self._last_value
        for i in range(count):
            point = self._intercept + self._phi * prev
            points[i] = point
            intervals.append(gaussian_intervals(point, self._residual_std))
            prev = point

        return ModelPrediction(
            points=points,
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(f"{self.name} must be fit() before predict()")


class RollingMeanBaseline:
    """Rolling-mean baseline: forecast equals the mean of the last `window` y values.

    Intervals use the std of in-sample errors y_t - mean(y_{t-window:t}).
    """

    name: str = "rolling_mean"
    version: str = "0.1.0"

    def __init__(self, window: int = 3) -> None:
        if window < 1:
            raise ValueError(f"window must be >= 1, got {window}")
        self.window = int(window)
        self._fitted: bool = False
        self._history: np.ndarray | None = None
        self._residual_std: float = 0.0

    def fit(self, X: Any, y: Any) -> Self:
        """Fit rolling-mean baseline on target history y.

        Inputs: X (ignored); y with at least `window` observations.
        Outputs: self (fitted).
        Time allowed to know: y in the training window only.
        """
        del X
        series = require_finite_1d(to_1d_float(y), name="y", min_len=self.window)
        self._history = series.copy()
        if series.size > self.window:
            residuals = np.empty(series.size - self.window, dtype=np.float64)
            for i, t in enumerate(range(self.window, series.size)):
                residuals[i] = series[t] - float(np.mean(series[t - self.window : t]))
            self._residual_std = residual_std(residuals)
        else:
            # Exactly one full window: no held-out in-sample error; scale 0.
            self._residual_std = 0.0
        self._fitted = True
        return self

    def predict(self, X: Any) -> ModelPrediction:
        """Predict the training-end rolling mean for each row of X.

        Inputs: X with one row per period to score (features unused).
        Outputs: ModelPrediction; point is constant across rows (no future y).
        Time allowed to know: last `window` training observations only.
        """
        self._require_fitted()
        assert self._history is not None
        count = n_rows(X)
        if count < 1:
            return ModelPrediction(
                points=np.asarray([], dtype=np.float64),
                intervals=[],
                model_name=self.name,
                model_version=self.version,
            )

        point = float(np.mean(self._history[-self.window :]))
        points = np.full(count, point, dtype=np.float64)
        intervals = [gaussian_intervals(point, self._residual_std) for _ in range(count)]
        return ModelPrediction(
            points=points,
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(f"{self.name} must be fit() before predict()")
