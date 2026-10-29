"""Protocol-compliant baseline doubles for harness tests.

Mirrors the three Modeling baselines (last value, AR(1), rolling mean) without
editing `nowcaster.models`. Used when real baselines are not yet importable.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from nowcaster.contracts import ModelPrediction, PredictionIntervals


def _intervals_from_point(point: float, sigma: float) -> PredictionIntervals:
    sigma = max(float(sigma), 1e-6)
    return PredictionIntervals(
        point=float(point),
        lower_80=float(point - 1.2816 * sigma),
        upper_80=float(point + 1.2816 * sigma),
        lower_95=float(point - 1.96 * sigma),
        upper_95=float(point + 1.96 * sigma),
    )


@dataclass
class LastValueBaseline:
    """Predict the last observed target value (naive persistence)."""

    name: str = "last_value"
    version: str = "test-double-0.1"
    _last: float | None = None
    _resid_std: float = 1.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LastValueBaseline:
        """Fit: store last y.

        Inputs: X (ignored), y (training targets).
        Outputs: self.
        Time allowed to know: training rows only.
        """
        values = np.asarray(y, dtype=float)
        if values.size == 0:
            raise ValueError("y must be non-empty")
        self._last = float(values[-1])
        if values.size >= 2:
            self._resid_std = float(np.std(np.diff(values))) or 1.0
        else:
            self._resid_std = 1.0
        return self

    def predict(self, X: pd.DataFrame) -> ModelPrediction:
        """Predict last value for each row of X.

        Inputs: X (row count drives output length; values ignored).
        Outputs: ModelPrediction.
        Time allowed to know: fitted training state only.
        """
        if self._last is None:
            raise RuntimeError("model not fitted")
        n = len(X)
        point = self._last
        intervals = [_intervals_from_point(point, self._resid_std) for _ in range(n)]
        return ModelPrediction(
            points=np.full(n, point, dtype=float),
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )


@dataclass
class AR1Baseline:
    """Simple AR(1) on the target: y_t = c + phi * y_{t-1}."""

    name: str = "ar1"
    version: str = "test-double-0.1"
    _phi: float = 0.0
    _c: float = 0.0
    _last: float | None = None
    _resid_std: float = 1.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> AR1Baseline:
        """Fit AR(1) by OLS on lag-1.

        Inputs: X (ignored), y (training targets).
        Outputs: self.
        Time allowed to know: training rows only.
        """
        values = np.asarray(y, dtype=float)
        if values.size < 2:
            self._phi = 0.0
            self._c = float(values[-1]) if values.size else 0.0
            self._last = self._c
            self._resid_std = 1.0
            return self
        y_lag = values[:-1]
        y_now = values[1:]
        # OLS: [1, y_lag] @ [c, phi] = y_now
        design = np.column_stack([np.ones(len(y_lag)), y_lag])
        coef, *_ = np.linalg.lstsq(design, y_now, rcond=None)
        self._c = float(coef[0])
        self._phi = float(coef[1])
        fitted = design @ coef
        resid = y_now - fitted
        self._resid_std = float(np.std(resid)) or 1.0
        self._last = float(values[-1])
        return self

    def predict(self, X: pd.DataFrame) -> ModelPrediction:
        """One-step AR(1) from last training observation.

        Inputs: X (length only).
        Outputs: ModelPrediction.
        Time allowed to know: fitted state only.
        """
        if self._last is None:
            raise RuntimeError("model not fitted")
        n = len(X)
        point = self._c + self._phi * self._last
        intervals = [_intervals_from_point(point, self._resid_std) for _ in range(n)]
        return ModelPrediction(
            points=np.full(n, point, dtype=float),
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )


@dataclass
class RollingMeanBaseline:
    """Predict the trailing mean of the target."""

    name: str = "rolling_mean"
    version: str = "test-double-0.1"
    window: int = 3
    _mean: float | None = None
    _resid_std: float = 1.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> RollingMeanBaseline:
        """Fit: trailing mean over up to `window` observations.

        Inputs: X (ignored), y (training targets).
        Outputs: self.
        Time allowed to know: training rows only.
        """
        values = np.asarray(y, dtype=float)
        if values.size == 0:
            raise ValueError("y must be non-empty")
        tail = values[-self.window :]
        self._mean = float(np.mean(tail))
        if values.size >= 2:
            self._resid_std = float(np.std(values - np.mean(values))) or 1.0
        else:
            self._resid_std = 1.0
        return self

    def predict(self, X: pd.DataFrame) -> ModelPrediction:
        """Predict fitted trailing mean.

        Inputs: X (length only).
        Outputs: ModelPrediction.
        Time allowed to know: fitted state only.
        """
        if self._mean is None:
            raise RuntimeError("model not fitted")
        n = len(X)
        point = self._mean
        intervals = [_intervals_from_point(point, self._resid_std) for _ in range(n)]
        return ModelPrediction(
            points=np.full(n, point, dtype=float),
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )


def baseline_double_factories() -> dict[str, type]:
    """Return name -> class for the three doubles (zero-arg constructible)."""
    return {
        "last_value": LastValueBaseline,
        "ar1": AR1Baseline,
        "rolling_mean": RollingMeanBaseline,
    }
