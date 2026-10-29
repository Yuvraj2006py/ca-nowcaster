"""Bridge regression: elastic-net nowcast of MoM GDP growth from features.

A bridge equation maps faster monthly indicators (the feature frame) onto the
slower target. Elastic net shrinks and selects among correlated MoM/YoY/lag
columns so the fit stays honest on short Canadian samples.

Inputs: X (feature frame), y (MoM growth) at fit; X rows at predict.
Outputs: ModelPrediction with Gaussian residual intervals.
Time allowed to know: only training rows passed to fit (CV stays inside fit).
"""

from __future__ import annotations

from typing import Any, Self

import numpy as np
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from nowcaster.contracts import ModelPrediction, PredictionIntervals
from nowcaster.models._array import (
    align_xy,
    median_impute_apply,
    median_impute_fit,
    n_rows,
    residual_std,
    to_2d_float,
)
from nowcaster.models.intervals import gaussian_intervals
from nowcaster.models.tuning import TuningResult, grid_search_timeseries


class BridgeRegression:
    """Elastic-net bridge regression with training-window hyperparameter search.

    Point: linear prediction from standardized imputed features.
    Intervals: Gaussian bands using in-sample residual std after the final fit.
    """

    name: str = "bridge"
    version: str = "0.1.0"

    def __init__(
        self,
        *,
        l1_ratios: tuple[float, ...] = (0.1, 0.5, 0.9),
        alphas: tuple[float, ...] = (0.01, 0.05, 0.1, 0.5, 1.0),
        max_iter: int = 5000,
        random_state: int = 0,
        n_cv_splits: int = 3,
        min_train_size: int = 12,
    ) -> None:
        self.l1_ratios = tuple(l1_ratios)
        self.alphas = tuple(alphas)
        self.max_iter = int(max_iter)
        self.random_state = int(random_state)
        self.n_cv_splits = int(n_cv_splits)
        self.min_train_size = int(min_train_size)
        self._fitted: bool = False
        self._medians: np.ndarray | None = None
        self._pipeline: Pipeline | None = None
        self._residual_std: float = 0.0
        self.tuning_evaluations: int = 0
        self.tuning_result: TuningResult | None = None
        self.best_params_: dict[str, Any] = {}

    def fit(self, X: Any, y: Any) -> Self:
        """Fit elastic-net bridge; tune alpha and l1_ratio inside the train window.

        Inputs: X feature matrix; y MoM growth aligned to X rows.
        Outputs: self (fitted). Logs ``tuning_evaluations`` = (#grid points)×(#folds).
        Time allowed to know: training X/y only; no future actuals.
        """
        X_arr, y_arr = align_xy(X, y)
        if y_arr.size < 2:
            raise ValueError(f"y needs at least 2 observations, got {y_arr.size}")
        if not np.isfinite(y_arr).all():
            raise ValueError("y contains non-finite values")

        self._medians = median_impute_fit(X_arr)
        X_imp = median_impute_apply(X_arr, self._medians)

        grid = [
            {"alpha": float(a), "l1_ratio": float(r)} for a in self.alphas for r in self.l1_ratios
        ]

        def _score(
            params: Any,
            X_tr: np.ndarray,
            y_tr: np.ndarray,
            X_va: np.ndarray,
            y_va: np.ndarray,
        ) -> float:
            pipe = self._make_pipeline(params["alpha"], params["l1_ratio"])
            pipe.fit(X_tr, y_tr)
            pred = pipe.predict(X_va)
            err = y_va - pred
            return float(np.sqrt(np.mean(err**2)))

        tuning = grid_search_timeseries(
            grid,
            X=X_imp,
            y=y_arr,
            fit_predict_score=_score,
            n_splits=self.n_cv_splits,
            min_train_size=self.min_train_size,
            higher_is_better=False,
        )
        self.tuning_result = tuning
        self.tuning_evaluations = int(tuning.n_evaluations)
        self.best_params_ = dict(tuning.best_params)

        pipe = self._make_pipeline(
            float(self.best_params_["alpha"]),
            float(self.best_params_["l1_ratio"]),
        )
        pipe.fit(X_imp, y_arr)
        fitted = pipe.predict(X_imp)
        self._residual_std = residual_std(y_arr - fitted)
        self._pipeline = pipe
        self._fitted = True
        return self

    def predict(self, X: Any) -> ModelPrediction:
        """Predict MoM growth and Gaussian 80%/95% intervals for each row of X.

        Inputs: X with the same feature columns as fit.
        Outputs: ModelPrediction aligned to rows of X.
        Time allowed to know: fitted coefficients and training residual scale only.
        """
        self._require_fitted()
        assert self._pipeline is not None and self._medians is not None
        count = n_rows(X)
        if count < 1:
            return ModelPrediction(
                points=np.asarray([], dtype=np.float64),
                intervals=[],
                model_name=self.name,
                model_version=self.version,
            )

        X_arr = to_2d_float(X)
        if X_arr.shape[1] != self._medians.shape[0]:
            raise ValueError(
                f"X has {X_arr.shape[1]} columns; bridge was fit with {self._medians.shape[0]}"
            )
        X_imp = median_impute_apply(X_arr, self._medians)
        points = np.asarray(self._pipeline.predict(X_imp), dtype=np.float64)
        intervals: list[PredictionIntervals] = [
            gaussian_intervals(float(p), self._residual_std) for p in points
        ]
        return ModelPrediction(
            points=points,
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )

    def _make_pipeline(self, alpha: float, l1_ratio: float) -> Pipeline:
        return Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "enet",
                    ElasticNet(
                        alpha=alpha,
                        l1_ratio=l1_ratio,
                        max_iter=self.max_iter,
                        random_state=self.random_state,
                        fit_intercept=True,
                    ),
                ),
            ]
        )

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(f"{self.name} must be fit() before predict()")
