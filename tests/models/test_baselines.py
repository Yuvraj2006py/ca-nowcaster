"""Unit tests for Phase 2 baselines against the NowcastModel contract."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nowcaster.contracts import ModelPrediction, NowcastModel, PredictionIntervals
from nowcaster.models import (
    AR1Baseline,
    LastValueBaseline,
    RollingMeanBaseline,
    create_baseline,
    gaussian_intervals,
    iter_baselines,
    list_baselines,
)
from nowcaster.models.intervals import Z_80, Z_95


def test_gaussian_intervals_symmetric() -> None:
    iv = gaussian_intervals(1.0, 2.0)
    assert iv.point == 1.0
    assert iv.lower_80 == pytest.approx(1.0 - Z_80 * 2.0)
    assert iv.upper_80 == pytest.approx(1.0 + Z_80 * 2.0)
    assert iv.lower_95 == pytest.approx(1.0 - Z_95 * 2.0)
    assert iv.upper_95 == pytest.approx(1.0 + Z_95 * 2.0)
    assert iv.lower_95 < iv.lower_80 < iv.point < iv.upper_80 < iv.upper_95


def test_list_baselines_order() -> None:
    assert list_baselines() == ["last_value", "ar1", "rolling_mean"]


@pytest.mark.parametrize(
    "name,cls",
    [
        ("last_value", LastValueBaseline),
        ("ar1", AR1Baseline),
        ("rolling_mean", RollingMeanBaseline),
    ],
)
def test_create_baseline_matches_class(name: str, cls: type) -> None:
    model = create_baseline(name)
    assert isinstance(model, cls)
    assert isinstance(model, NowcastModel)
    assert model.name == name
    assert model.version == "0.1.0"


def test_create_baseline_unknown() -> None:
    with pytest.raises(KeyError, match="Unknown baseline"):
        create_baseline("bridge_regression")


def test_rolling_mean_window_kwarg() -> None:
    model = create_baseline("rolling_mean", window=6)
    assert isinstance(model, RollingMeanBaseline)
    assert model.window == 6


def _assert_prediction_shape(pred: ModelPrediction, n: int, name: str) -> None:
    assert pred.model_name == name
    assert pred.model_version == "0.1.0"
    points = np.asarray(pred.points, dtype=np.float64)
    assert points.shape == (n,)
    assert len(pred.intervals) == n
    for i, iv in enumerate(pred.intervals):
        assert isinstance(iv, PredictionIntervals)
        assert iv.point == pytest.approx(float(points[i]))
        assert iv.lower_95 <= iv.lower_80 <= iv.point <= iv.upper_80 <= iv.upper_95


def test_last_value_predicts_training_end(
    train_xy: tuple[pd.DataFrame, pd.Series],
    test_x: pd.DataFrame,
) -> None:
    X_train, y_train = train_xy
    model = LastValueBaseline().fit(X_train, y_train)
    pred = model.predict(test_x)
    _assert_prediction_shape(pred, len(test_x), "last_value")
    expected = float(y_train.iloc[-1])
    assert np.allclose(pred.points, expected)


def test_ar1_one_step_matches_ols(
    train_xy: tuple[pd.DataFrame, pd.Series],
) -> None:
    X_train, y_train = train_xy
    y = y_train.to_numpy(dtype=np.float64)
    design = np.column_stack([np.ones(len(y) - 1), y[:-1]])
    coef, _, _, _ = np.linalg.lstsq(design, y[1:], rcond=None)
    expected = float(coef[0] + coef[1] * y[-1])

    model = AR1Baseline().fit(X_train, y_train)
    pred = model.predict(pd.DataFrame(index=y_train.index[-1:]))
    assert float(pred.points[0]) == pytest.approx(expected)


def test_ar1_chains_multi_step(
    train_xy: tuple[pd.DataFrame, pd.Series],
    test_x: pd.DataFrame,
) -> None:
    X_train, y_train = train_xy
    model = AR1Baseline().fit(X_train, y_train)
    pred = model.predict(test_x)
    _assert_prediction_shape(pred, 3, "ar1")
    # Second step uses first predicted point as lag, not a future actual.
    p0 = float(pred.points[0])
    expected_p1 = model._intercept + model._phi * p0
    assert float(pred.points[1]) == pytest.approx(expected_p1)


def test_rolling_mean_uses_last_window(
    train_xy: tuple[pd.DataFrame, pd.Series],
    test_x: pd.DataFrame,
) -> None:
    X_train, y_train = train_xy
    window = 3
    model = RollingMeanBaseline(window=window).fit(X_train, y_train)
    pred = model.predict(test_x)
    _assert_prediction_shape(pred, len(test_x), "rolling_mean")
    expected = float(y_train.iloc[-window:].mean())
    assert np.allclose(pred.points, expected)


def test_predict_before_fit_raises(test_x: pd.DataFrame) -> None:
    for model in (LastValueBaseline(), AR1Baseline(), RollingMeanBaseline()):
        with pytest.raises(RuntimeError, match="fit"):
            model.predict(test_x)


def test_ar1_requires_two_points() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        AR1Baseline().fit(pd.DataFrame(index=[0]), pd.Series([1.0]))


def test_rolling_mean_requires_window_length() -> None:
    with pytest.raises(ValueError, match="at least 3"):
        RollingMeanBaseline(window=3).fit(
            pd.DataFrame(index=[0, 1]),
            pd.Series([0.1, 0.2]),
        )


def test_harness_loop_no_model_code_changes(
    train_xy: tuple[pd.DataFrame, pd.Series],
    test_x: pd.DataFrame,
) -> None:
    """Evaluation-shaped loop: registry only; no per-model branches."""
    X_train, y_train = train_xy
    results: dict[str, ModelPrediction] = {}
    for model in iter_baselines():
        fitted = model.fit(X_train, y_train)
        assert isinstance(fitted, NowcastModel)
        results[model.name] = fitted.predict(test_x)

    assert set(results) == {"last_value", "ar1", "rolling_mean"}
    for name, pred in results.items():
        _assert_prediction_shape(pred, len(test_x), name)


def test_fit_accepts_numpy_without_features() -> None:
    y = np.array([0.1, 0.2, 0.15, 0.05, -0.02, 0.08], dtype=np.float64)
    X = np.zeros((len(y), 0), dtype=np.float64)
    X_test = np.zeros((2, 0), dtype=np.float64)
    for model in iter_baselines():
        pred = model.fit(X, y).predict(X_test)
        _assert_prediction_shape(pred, 2, model.name)
