"""Gradient-boosting nowcast of MoM GDP growth (sklearn HistGradientBoosting).

Trees capture nonlinear interactions among indicators that a linear bridge may
miss. Prediction intervals use split conformal absolute residuals estimated on
a chronological calibration slice of the training window (not the test fold).

Inputs: X (features), y (MoM growth) at fit; X rows at predict.
Outputs: ModelPrediction with conformal 80%/95% intervals.
Time allowed to know: training rows only; tuning and calibration stay in-fit.
"""

from __future__ import annotations

from typing import Any, Self

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from nowcaster.contracts import ModelPrediction, PredictionIntervals
from nowcaster.models._array import align_xy, n_rows, require_feature_matrix, to_2d_float
from nowcaster.models.intervals import conformal_intervals
from nowcaster.models.tuning import TuningResult, grid_search_timeseries


class GradientBoostingNowcast:
    """HistGradientBoostingRegressor with train-window tuning and conformal bands."""

    name: str = "gradient_boosting"
    version: str = "0.1.0"

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
        if not 0.05 <= calibration_fraction <= 0.5:
            raise ValueError("calibration_fraction should be in [0.05, 0.5]")
        self.max_depth_grid = tuple(max_depth_grid)
        self.learning_rate_grid = tuple(learning_rate_grid)
        self.max_iter_grid = tuple(max_iter_grid)
        self.n_cv_splits = int(n_cv_splits)
        self.min_train_size = int(min_train_size)
        self.calibration_fraction = float(calibration_fraction)
        self.random_state = int(random_state)
        self._fitted: bool = False
        self._model: HistGradientBoostingRegressor | None = None
        self._abs_residuals: np.ndarray = np.asarray([], dtype=np.float64)
        self._n_features: int = 0
        self.tuning_evaluations: int = 0
        self.tuning_result: TuningResult | None = None
        self.best_params_: dict[str, Any] = {}

    def fit(self, X: Any, y: Any) -> Self:
        """Tune and fit GBM on train; reserve a tail slice for conformal residuals.

        Inputs: X feature matrix (NaNs allowed — HGB handles them); y MoM growth.
        Outputs: self (fitted). Logs ``tuning_evaluations``.
        Time allowed to know: training X/y only.
        """
        X_arr, y_arr = align_xy(X, y)
        if y_arr.size < max(self.min_train_size, 8):
            raise ValueError(f"y needs more history for GBM, got {y_arr.size}")
        if not np.isfinite(y_arr).all():
            raise ValueError("y contains non-finite values")
        self._n_features = int(X_arr.shape[1])

        n = y_arr.size
        cal_size = max(3, int(round(n * self.calibration_fraction)))
        cal_size = min(cal_size, n // 3)
        tune_end = n - cal_size
        if tune_end < self.min_train_size:
            tune_end = n
            cal_size = 0

        X_tune, y_tune = X_arr[:tune_end], y_arr[:tune_end]
        grid = [
            {
                "max_depth": int(d),
                "learning_rate": float(lr),
                "max_iter": int(m),
            }
            for d in self.max_depth_grid
            for lr in self.learning_rate_grid
            for m in self.max_iter_grid
        ]

        def _score(
            params: Any,
            X_tr: np.ndarray,
            y_tr: np.ndarray,
            X_va: np.ndarray,
            y_va: np.ndarray,
        ) -> float:
            model = self._make_model(params)
            model.fit(X_tr, y_tr)
            pred = model.predict(X_va)
            err = y_va - pred
            return float(np.sqrt(np.mean(err**2)))

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

        # Fit on pre-calibration window; score absolute residuals on calibration tail.
        if cal_size >= 3:
            model = self._make_model(self.best_params_)
            model.fit(X_arr[:tune_end], y_arr[:tune_end])
            cal_pred = model.predict(X_arr[tune_end:])
            self._abs_residuals = np.abs(y_arr[tune_end:] - cal_pred)
            # Refit on full training window with the same hyperparameters.
            full = self._make_model(self.best_params_)
            full.fit(X_arr, y_arr)
            self._model = full
        else:
            model = self._make_model(self.best_params_)
            model.fit(X_arr, y_arr)
            self._model = model
            # Fallback: in-sample absolute residuals (slightly optimistic).
            self._abs_residuals = np.abs(y_arr - model.predict(X_arr))

        self._fitted = True
        return self

    def predict(self, X: Any) -> ModelPrediction:
        """Predict MoM growth with conformal 80%/95% intervals.

        Inputs: X feature rows matching fit width.
        Outputs: ModelPrediction aligned to rows of X.
        Time allowed to know: fitted trees + calibration residuals only.
        """
        self._require_fitted()
        assert self._model is not None
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
            raise ValueError(f"X has {X_arr.shape[1]} columns; GBM was fit with {self._n_features}")
        # ensure feature matrix contract even if caller passes a single series
        require_feature_matrix(X_arr, min_cols=1)
        points = np.asarray(self._model.predict(X_arr), dtype=np.float64)
        intervals: list[PredictionIntervals] = [
            conformal_intervals(float(p), self._abs_residuals) for p in points
        ]
        return ModelPrediction(
            points=points,
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )

    def _make_model(self, params: dict[str, Any]) -> HistGradientBoostingRegressor:
        return HistGradientBoostingRegressor(
            max_depth=int(params["max_depth"]),
            learning_rate=float(params["learning_rate"]),
            max_iter=int(params["max_iter"]),
            random_state=self.random_state,
        )

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(f"{self.name} must be fit() before predict()")
