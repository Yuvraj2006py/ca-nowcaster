"""Direction classifiers for the secondary nowcast target.

Secondary target: did MoM growth beat the previous month (binary). Labels are
derived from the primary ``y`` series inside ``fit``; Evaluation still passes
the same (X, y) as for regression models.

Two registered models:
  - ``direction_classifier`` — L2 logistic regression with CV-tuned C, then
    probability calibration on a train calibration fold (primary / expected name).
  - ``direction_boosting`` — HistGradientBoostingClassifier + calibration
    (comparison model; same secondary target).

Point predictions are calibrated probabilities in [0, 1]. Intervals are
conformal bands on the probability scale, clipped to [0, 1].

Inputs: X features; y MoM growth (used to build beat-previous labels).
Outputs: ModelPrediction (probability point + intervals).
Time allowed to know: training window only.
"""

from __future__ import annotations

from typing import Any, Self

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from nowcaster.contracts import ModelPrediction, PredictionIntervals
from nowcaster.models._array import (
    align_xy,
    median_impute_apply,
    median_impute_fit,
    n_rows,
    to_2d_float,
)
from nowcaster.models.intervals import clip_unit_interval, conformal_intervals
from nowcaster.models.tuning import TuningResult, grid_search_timeseries


def beat_previous_labels(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Build binary labels: 1 if y_t > y_{t-1}, else 0 (drop t=0).

    Inputs: ordered MoM growth series from the training window.
    Outputs: (row_indices into y/X starting at 1, label array).
    Time allowed to know: training y only.
    """
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    if y.size < 2:
        raise ValueError("need at least 2 observations to form beat-previous labels")
    if not np.isfinite(y).all():
        raise ValueError("y contains non-finite values")
    labels = (y[1:] > y[:-1]).astype(np.float64)
    indices = np.arange(1, y.size, dtype=np.int64)
    return indices, labels


class _DirectionBase:
    """Shared fit/predict plumbing for direction classifiers."""

    name: str
    version: str = "0.1.0"
    needs_impute: bool = True

    def __init__(
        self,
        *,
        n_cv_splits: int = 3,
        min_train_size: int = 12,
        calibration_fraction: float = 0.25,
        random_state: int = 0,
    ) -> None:
        if not 0.05 <= calibration_fraction <= 0.5:
            raise ValueError("calibration_fraction should be in [0.05, 0.5]")
        self.n_cv_splits = int(n_cv_splits)
        self.min_train_size = int(min_train_size)
        self.calibration_fraction = float(calibration_fraction)
        self.random_state = int(random_state)
        self._fitted: bool = False
        self._estimator: Any = None
        self._medians: np.ndarray | None = None
        self._n_features: int = 0
        self._abs_residuals: np.ndarray = np.asarray([], dtype=np.float64)
        self.tuning_evaluations: int = 0
        self.tuning_result: TuningResult | None = None
        self.best_params_: dict[str, Any] = {}

    def fit(self, X: Any, y: Any) -> Self:
        """Derive beat-previous labels, tune, calibrate, and store conformal residuals.

        Inputs: X features; y MoM growth (labels derived as y_t > y_{t-1}).
        Outputs: self (fitted). Logs ``tuning_evaluations``.
        Time allowed to know: training X/y only.
        """
        X_arr, y_arr = align_xy(X, y)
        indices, labels = beat_previous_labels(y_arr)
        X_sup = X_arr[indices]
        y_sup = labels
        if y_sup.size < max(8, self.min_train_size // 2):
            raise ValueError(f"not enough labeled direction rows after lag drop: {y_sup.size}")
        # Need both classes for logistic / calibration.
        if np.unique(y_sup).size < 2:
            raise ValueError("direction labels are constant in the training window")

        self._n_features = int(X_sup.shape[1])
        if self.needs_impute:
            self._medians = median_impute_fit(X_sup)
            X_sup = median_impute_apply(X_sup, self._medians)
        else:
            self._medians = None

        n = y_sup.size
        cal_size = max(3, int(round(n * self.calibration_fraction)))
        cal_size = min(cal_size, n // 3)
        tune_end = n - cal_size
        if tune_end < max(6, self.min_train_size // 2):
            tune_end = n
            cal_size = 0

        X_tune, y_tune = X_sup[:tune_end], y_sup[:tune_end]
        grid = self._param_grid()

        def _score(
            params: Any,
            X_tr: np.ndarray,
            y_tr: np.ndarray,
            X_va: np.ndarray,
            y_va: np.ndarray,
        ) -> float:
            if np.unique(y_tr).size < 2:
                return float("inf")
            clf = self._make_base(params)
            clf.fit(X_tr, y_tr)
            # Prefer probability log-loss when available; else 0-1 error.
            if hasattr(clf, "predict_proba"):
                proba = clf.predict_proba(X_va)[:, 1]
                eps = 1e-6
                proba = np.clip(proba, eps, 1.0 - eps)
                loss = y_va * np.log(proba) + (1.0 - y_va) * np.log(1.0 - proba)
                return float(-np.mean(loss))
            pred = clf.predict(X_va)
            return float(np.mean(pred != y_va))

        tuning = grid_search_timeseries(
            grid,
            X=X_tune,
            y=y_tune,
            fit_predict_score=_score,
            n_splits=self.n_cv_splits,
            min_train_size=min(self.min_train_size, max(6, tune_end // 3)),
            higher_is_better=False,
        )
        self.tuning_result = tuning
        self.tuning_evaluations = int(tuning.n_evaluations)
        self.best_params_ = dict(tuning.best_params)

        if cal_size >= 3 and np.unique(y_sup[:tune_end]).size >= 2:
            # Fit on the pre-calibration window; absolute probability residuals on
            # the held-out calibration tail feed conformal intervals. Final
            # estimator is recalibrated on the full supervised sample below.
            base = self._make_base(self.best_params_)
            base.fit(X_sup[:tune_end], y_sup[:tune_end])
            self._estimator = base
            cal_proba = self._predict_proba_rows(X_sup[tune_end:])
            self._abs_residuals = np.abs(y_sup[tune_end:] - cal_proba)
            self._estimator = self._fit_calibrated(X_sup, y_sup)
        else:
            self._estimator = self._fit_calibrated(X_sup, y_sup)
            proba = self._predict_proba_rows(X_sup)
            self._abs_residuals = np.abs(y_sup - proba)

        self._fitted = True
        return self

    def predict(self, X: Any) -> ModelPrediction:
        """Predict calibrated P(growth beats previous month) with intervals.

        Inputs: X feature rows for the months being scored.
        Outputs: ModelPrediction; point in [0, 1]; intervals clipped to [0, 1].
        Time allowed to know: fitted classifier + train calibration residuals.
        """
        self._require_fitted()
        assert self._estimator is not None
        count = n_rows(X)
        if count < 1:
            return ModelPrediction(
                points=np.asarray([], dtype=np.float64),
                intervals=[],
                model_name=self.name,
                model_version=self.version,
            )

        X_arr = to_2d_float(X)
        if X_arr.shape[1] != self._n_features:
            raise ValueError(
                f"X has {X_arr.shape[1]} columns; classifier was fit with {self._n_features}"
            )
        if self.needs_impute:
            assert self._medians is not None
            X_arr = median_impute_apply(X_arr, self._medians)

        points = self._predict_proba_rows(X_arr)
        intervals: list[PredictionIntervals] = [
            clip_unit_interval(conformal_intervals(float(p), self._abs_residuals)) for p in points
        ]
        return ModelPrediction(
            points=points,
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )

    def _fit_calibrated(self, X: np.ndarray, y: np.ndarray) -> Any:
        """Fit base classifier with sigmoid calibration when class counts allow.

        Inputs: supervised feature/label rows from the training window only.
        Outputs: CalibratedClassifierCV or fitted base if CV calibration fails.
        Time allowed to know: X/y rows passed in (training window subset).
        """
        base = self._make_base(self.best_params_)
        counts = np.bincount(y.astype(int), minlength=2)
        n_folds = min(3, int(counts.min()))
        try:
            if n_folds < 2:
                raise ValueError("need at least 2 samples per class for calibration CV")
            calib = CalibratedClassifierCV(base, method="sigmoid", cv=n_folds)
            calib.fit(X, y)
            return calib
        except ValueError:
            base.fit(X, y)
            return base

    def _predict_proba_rows(self, X: np.ndarray) -> np.ndarray:
        est = self._estimator
        if hasattr(est, "predict_proba"):
            proba = np.asarray(est.predict_proba(X), dtype=np.float64)
            if proba.ndim == 2 and proba.shape[1] >= 2:
                return proba[:, 1]
            return proba.reshape(-1)
        # Decision-function fallback → sigmoid
        if hasattr(est, "decision_function"):
            z = np.asarray(est.decision_function(X), dtype=np.float64).reshape(-1)
            return 1.0 / (1.0 + np.exp(-z))
        return np.asarray(est.predict(X), dtype=np.float64).reshape(-1)

    def _param_grid(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def _make_base(self, params: dict[str, Any]) -> Any:
        raise NotImplementedError

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(f"{self.name} must be fit() before predict()")


class DirectionLogistic(_DirectionBase):
    """L2-regularized logistic regression direction classifier (calibrated).

    Registered as ``direction_classifier`` (Evaluation Phase 3 expected name).
    """

    name: str = "direction_classifier"
    needs_impute: bool = True

    def __init__(
        self,
        *,
        C_grid: tuple[float, ...] = (0.1, 1.0, 10.0),
        n_cv_splits: int = 3,
        min_train_size: int = 12,
        calibration_fraction: float = 0.25,
        random_state: int = 0,
    ) -> None:
        super().__init__(
            n_cv_splits=n_cv_splits,
            min_train_size=min_train_size,
            calibration_fraction=calibration_fraction,
            random_state=random_state,
        )
        self.C_grid = tuple(float(c) for c in C_grid)

    def _param_grid(self) -> list[dict[str, Any]]:
        return [{"C": c} for c in self.C_grid]

    def _make_base(self, params: dict[str, Any]) -> Any:
        return Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        C=float(params["C"]),
                        penalty="l2",
                        solver="lbfgs",
                        max_iter=2000,
                        random_state=self.random_state,
                    ),
                ),
            ]
        )


class DirectionBoosting(_DirectionBase):
    """Gradient-boosting direction classifier with calibrated probabilities."""

    name: str = "direction_boosting"
    needs_impute: bool = False  # HGB handles NaNs

    def __init__(
        self,
        *,
        max_depth_grid: tuple[int, ...] = (2, 3),
        learning_rate_grid: tuple[float, ...] = (0.05, 0.1),
        max_iter_grid: tuple[int, ...] = (100, 200),
        n_cv_splits: int = 3,
        min_train_size: int = 12,
        calibration_fraction: float = 0.25,
        random_state: int = 0,
    ) -> None:
        super().__init__(
            n_cv_splits=n_cv_splits,
            min_train_size=min_train_size,
            calibration_fraction=calibration_fraction,
            random_state=random_state,
        )
        self.max_depth_grid = tuple(max_depth_grid)
        self.learning_rate_grid = tuple(learning_rate_grid)
        self.max_iter_grid = tuple(max_iter_grid)

    def _param_grid(self) -> list[dict[str, Any]]:
        return [
            {
                "max_depth": int(d),
                "learning_rate": float(lr),
                "max_iter": int(m),
            }
            for d in self.max_depth_grid
            for lr in self.learning_rate_grid
            for m in self.max_iter_grid
        ]

    def _make_base(self, params: dict[str, Any]) -> Any:
        return HistGradientBoostingClassifier(
            max_depth=int(params["max_depth"]),
            learning_rate=float(params["learning_rate"]),
            max_iter=int(params["max_iter"]),
            random_state=self.random_state,
        )
