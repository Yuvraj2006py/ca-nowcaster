"""Dynamic factor nowcast via statsmodels DynamicFactorMQ.

Treats the monthly feature frame plus the target as a ragged panel, extracts a
small number of latent factors, and reads the filtered expectation of the
target when the latest GDP observation is missing (classic nowcast setup).

Inputs: X (features), y (MoM growth) at fit; feature rows at predict.
Outputs: ModelPrediction; intervals from Gaussian training prediction errors.
Time allowed to know: training panel only; predict may not see future actuals.
"""

from __future__ import annotations

from typing import Any, Self

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.dynamic_factor_mq import DynamicFactorMQ

from nowcaster.contracts import ModelPrediction, PredictionIntervals
from nowcaster.models._array import (
    align_xy,
    column_names,
    n_rows,
    residual_std,
    to_2d_float,
)
from nowcaster.models.intervals import gaussian_intervals
from nowcaster.models.tuning import TuningResult, grid_search_timeseries

_TARGET_COL = "__target_mom__"


class DynamicFactorNowcast:
    """DynamicFactorMQ wrapper implementing the NowcastModel interface.

    Hyperparameters ``factors`` and ``factor_orders`` are chosen by expanding
    CV RMSE inside the training window. Tuning evaluation counts are logged on
    ``tuning_evaluations``.
    """

    name: str = "dynamic_factor"
    version: str = "0.1.0"

    def __init__(
        self,
        *,
        factor_grid: tuple[int, ...] = (1, 2),
        order_grid: tuple[int, ...] = (1, 2),
        maxiter: int = 100,
        n_cv_splits: int = 2,
        min_train_size: int = 18,
        idiosyncratic_ar1: bool = False,
        standardize: bool = True,
        random_state: int = 0,
    ) -> None:
        self.factor_grid = tuple(int(k) for k in factor_grid)
        self.order_grid = tuple(int(p) for p in order_grid)
        self.maxiter = int(maxiter)
        self.n_cv_splits = int(n_cv_splits)
        self.min_train_size = int(min_train_size)
        self.idiosyncratic_ar1 = bool(idiosyncratic_ar1)
        self.standardize = bool(standardize)
        self.random_state = int(random_state)
        self._fitted: bool = False
        self._results: Any = None
        self._feature_names: list[str] = []
        self._residual_std: float = 0.0
        self._train_endog: pd.DataFrame | None = None
        self._next_row_index: int = 0
        self.tuning_evaluations: int = 0
        self.tuning_result: TuningResult | None = None
        self.best_params_: dict[str, Any] = {}

    def fit(self, X: Any, y: Any) -> Self:
        """Fit DynamicFactorMQ on features+target; tune factors/orders on train.

        Inputs: X feature matrix; y MoM growth (finite) aligned to X.
        Outputs: self (fitted). ``tuning_evaluations`` counts CV EM fits.
        Time allowed to know: training X/y only.
        """
        X_arr, y_arr = align_xy(X, y)
        if y_arr.size < self.min_train_size:
            raise ValueError(
                f"y needs at least {self.min_train_size} observations for DFM, got {y_arr.size}"
            )
        if not np.isfinite(y_arr).all():
            raise ValueError("y contains non-finite values")

        self._feature_names = column_names(X, X_arr.shape[1])
        endog = self._build_endog(X_arr, y_arr, start=0)

        grid = [
            {"factors": int(k), "factor_orders": int(p)}
            for k in self.factor_grid
            for p in self.order_grid
        ]

        # Dummy X for TimeSeriesSplit indices; y drives the actual data via endog.
        X_index = np.arange(X_arr.shape[0], dtype=np.float64).reshape(-1, 1)

        def _score(
            params: Any,
            X_tr: np.ndarray,
            y_tr: np.ndarray,
            X_va: np.ndarray,
            y_va: np.ndarray,
        ) -> float:
            del X_tr, X_va  # expanding CV prefixes; sizes recover positions
            n_tr = y_tr.shape[0]
            n_va = y_va.shape[0]
            train_endog = endog.iloc[:n_tr]
            try:
                res = self._fit_dfm(train_endog, params["factors"], params["factor_orders"])
            except Exception:
                return float("inf")
            va_block = endog.iloc[n_tr : n_tr + n_va].copy()
            va_block[_TARGET_COL] = np.nan
            try:
                appended = res.append(va_block, refit=False)
                pred = np.asarray(appended.predict()[_TARGET_COL].iloc[-n_va:], dtype=np.float64)
            except Exception:
                return float("inf")
            if pred.shape[0] != n_va or not np.isfinite(pred).all():
                return float("inf")
            err = y_va - pred
            return float(np.sqrt(np.mean(err**2)))

        tuning = grid_search_timeseries(
            grid,
            X=X_index,
            y=y_arr,
            fit_predict_score=_score,
            n_splits=self.n_cv_splits,
            min_train_size=self.min_train_size,
            higher_is_better=False,
        )
        self.tuning_result = tuning
        self.tuning_evaluations = int(tuning.n_evaluations)
        self.best_params_ = dict(tuning.best_params)

        factors = int(self.best_params_.get("factors", self.factor_grid[0]))
        orders = int(self.best_params_.get("factor_orders", self.order_grid[0]))
        self._results = self._fit_dfm(endog, factors, orders)
        self._train_endog = endog
        self._next_row_index = int(endog.index[-1]) + 1

        # In-sample one-step prediction errors for residual scale.
        in_sample = np.asarray(self._results.predict()[_TARGET_COL], dtype=np.float64)
        self._residual_std = residual_std(y_arr - in_sample)
        self._fitted = True
        return self

    def predict(self, X: Any) -> ModelPrediction:
        """Nowcast target by appending feature rows with masked y to the DFM.

        Inputs: X feature rows (same columns as fit); y unknown → treated as NaN.
        Outputs: ModelPrediction from filtered target expectations.
        Time allowed to know: fitted DFM state and X features only (no y actuals).
        """
        self._require_fitted()
        assert self._results is not None and self._train_endog is not None
        count = n_rows(X)
        if count < 1:
            return ModelPrediction(
                points=np.asarray([], dtype=np.float64),
                intervals=[],
                model_name=self.name,
                model_version=self.version,
            )

        X_arr = to_2d_float(X)
        if X_arr.shape[1] != len(self._feature_names):
            raise ValueError(
                f"X has {X_arr.shape[1]} columns; DFM was fit with {len(self._feature_names)}"
            )

        new_endog = self._frame_from_features(X_arr, y=None, start=self._next_row_index)
        # Prefer append when the index continues; fall back to smooth-on-extended panel.
        try:
            appended = self._results.append(new_endog, refit=False)
            pred_series = appended.predict()[_TARGET_COL].iloc[-count:]
        except (ValueError, KeyError):
            extended = pd.concat([self._train_endog, new_endog], axis=0)
            factors = int(self.best_params_.get("factors", self.factor_grid[0]))
            orders = int(self.best_params_.get("factor_orders", self.order_grid[0]))
            model = DynamicFactorMQ(
                extended,
                factors=factors,
                factor_orders=orders,
                idiosyncratic_ar1=self.idiosyncratic_ar1,
                standardize=self.standardize,
            )
            smoothed = model.smooth(self._results.params)
            pred_series = smoothed.predict()[_TARGET_COL].iloc[-count:]

        points = np.asarray(pred_series, dtype=np.float64)
        if points.shape[0] != count:
            raise RuntimeError(
                f"DFM predict length mismatch: got {points.shape[0]}, expected {count}"
            )
        if not np.isfinite(points).all():
            # Fall back to last training filtered value if filter returns NaN.
            last = float(self._results.predict()[_TARGET_COL].iloc[-1])
            points = np.where(np.isfinite(points), points, last)

        intervals: list[PredictionIntervals] = [
            gaussian_intervals(float(p), self._residual_std) for p in points
        ]
        return ModelPrediction(
            points=points,
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )

    def _fit_dfm(self, endog: pd.DataFrame, factors: int, factor_orders: int) -> Any:
        model = DynamicFactorMQ(
            endog,
            factors=factors,
            factor_orders=factor_orders,
            idiosyncratic_ar1=self.idiosyncratic_ar1,
            standardize=self.standardize,
        )
        return model.fit(disp=False, maxiter=self.maxiter)

    def _build_endog(self, X_arr: np.ndarray, y_arr: np.ndarray, *, start: int) -> pd.DataFrame:
        return self._frame_from_features(X_arr, y=y_arr, start=start)

    def _frame_from_features(
        self,
        X_arr: np.ndarray,
        y: np.ndarray | None,
        *,
        start: int,
    ) -> pd.DataFrame:
        n = X_arr.shape[0]
        idx = pd.RangeIndex(start, start + n)
        data = {name: X_arr[:, j] for j, name in enumerate(self._feature_names)}
        if y is None:
            data[_TARGET_COL] = np.full(n, np.nan, dtype=np.float64)
        else:
            data[_TARGET_COL] = np.asarray(y, dtype=np.float64)
        return pd.DataFrame(data, index=idx)

    def _require_fitted(self) -> None:
        if not self._fitted:
            raise RuntimeError(f"{self.name} must be fit() before predict()")
