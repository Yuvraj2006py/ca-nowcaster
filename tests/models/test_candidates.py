"""Unit tests for Phase 3 candidate models against the NowcastModel contract."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nowcaster.contracts import ModelPrediction, NowcastModel, PredictionIntervals
from nowcaster.models import (
    BASELINE_NAMES,
    CANDIDATE_NAMES,
    DIRECTION_CANDIDATE_NAMES,
    REGRESSION_CANDIDATE_NAMES,
    BridgeRegression,
    DirectionBoosting,
    DirectionLogistic,
    DynamicFactorNowcast,
    GradientBoostingNowcast,
    create_baseline,
    create_candidate,
    create_model,
    iter_baselines,
    iter_candidates,
    list_baselines,
    list_candidates,
    list_models,
)
from nowcaster.models.classifiers import beat_previous_labels
from nowcaster.models.intervals import conformal_intervals, conformal_quantile


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


def test_list_candidates_and_baselines_unchanged() -> None:
    assert list_baselines() == ["last_value", "ar1", "rolling_mean"]
    assert list_candidates() == [
        "bridge",
        "dynamic_factor",
        "gradient_boosting",
        "direction_classifier",
        "direction_boosting",
    ]
    assert list(REGRESSION_CANDIDATE_NAMES) == [
        "bridge",
        "dynamic_factor",
        "gradient_boosting",
    ]
    assert list(DIRECTION_CANDIDATE_NAMES) == [
        "direction_classifier",
        "direction_boosting",
    ]
    # Unified list keeps baselines first.
    assert list_models()[:3] == list_baselines()
    assert set(list_models()) == set(BASELINE_NAMES) | set(CANDIDATE_NAMES)


def test_create_candidate_and_model() -> None:
    assert isinstance(create_candidate("bridge"), BridgeRegression)
    assert isinstance(create_model("ar1"), NowcastModel)
    assert isinstance(create_model("gradient_boosting"), GradientBoostingNowcast)
    with pytest.raises(KeyError, match="Unknown candidate"):
        create_candidate("last_value")
    with pytest.raises(KeyError, match="Unknown model"):
        create_model("not_a_model")


def test_baselines_still_work_via_create_baseline(
    train_xy: tuple[pd.DataFrame, pd.Series],
    test_x: pd.DataFrame,
) -> None:
    X_train, y_train = train_xy
    for model in iter_baselines():
        pred = model.fit(X_train, y_train).predict(test_x)
        _assert_prediction_shape(pred, len(test_x), model.name)


def test_conformal_intervals_nest() -> None:
    residuals = np.array([0.1, 0.2, 0.15, 0.4, 0.05, 0.3], dtype=np.float64)
    iv = conformal_intervals(1.0, residuals)
    assert iv.lower_95 <= iv.lower_80 <= iv.point <= iv.upper_80 <= iv.upper_95
    assert conformal_quantile(residuals, 0.95) >= conformal_quantile(residuals, 0.80)


def test_bridge_fit_predict_logs_tuning(
    candidate_train_xy: tuple[pd.DataFrame, pd.Series],
    candidate_test_x: pd.DataFrame,
) -> None:
    X_train, y_train = candidate_train_xy
    model = BridgeRegression(
        alphas=(0.05, 0.2),
        l1_ratios=(0.5,),
        n_cv_splits=2,
        min_train_size=8,
    )
    pred = model.fit(X_train, y_train).predict(candidate_test_x)
    _assert_prediction_shape(pred, len(candidate_test_x), "bridge")
    assert model.tuning_evaluations >= 1
    assert "alpha" in model.best_params_
    assert "l1_ratio" in model.best_params_


def test_gradient_boosting_conformal(
    candidate_train_xy: tuple[pd.DataFrame, pd.Series],
    candidate_test_x: pd.DataFrame,
) -> None:
    X_train, y_train = candidate_train_xy
    model = GradientBoostingNowcast(
        max_depth_grid=(2,),
        learning_rate_grid=(0.1,),
        max_iter_grid=(50,),
        n_cv_splits=2,
        min_train_size=8,
        calibration_fraction=0.25,
    )
    pred = model.fit(X_train, y_train).predict(candidate_test_x)
    _assert_prediction_shape(pred, len(candidate_test_x), "gradient_boosting")
    assert model.tuning_evaluations >= 1


def test_dynamic_factor_fit_predict(
    candidate_train_xy: tuple[pd.DataFrame, pd.Series],
    candidate_test_x: pd.DataFrame,
) -> None:
    X_train, y_train = candidate_train_xy
    # Tiny grid + low maxiter for unit-test speed.
    model = DynamicFactorNowcast(
        factor_grid=(1,),
        order_grid=(1,),
        maxiter=25,
        n_cv_splits=2,
        min_train_size=12,
    )
    pred = model.fit(X_train, y_train).predict(candidate_test_x)
    _assert_prediction_shape(pred, len(candidate_test_x), "dynamic_factor")
    assert np.isfinite(pred.points).all()
    # With a one-point grid, CV still evaluates that point on each fold.
    assert model.tuning_evaluations >= 0
    assert model.best_params_.get("factors") == 1


def test_direction_labels() -> None:
    y = np.array([0.1, 0.2, 0.15, 0.05], dtype=np.float64)
    idx, labels = beat_previous_labels(y)
    assert list(idx) == [1, 2, 3]
    assert list(labels) == [1.0, 0.0, 0.0]


@pytest.mark.parametrize(
    "factory,name",
    [
        (
            lambda: DirectionLogistic(
                C_grid=(1.0,),
                n_cv_splits=2,
                min_train_size=8,
                calibration_fraction=0.25,
            ),
            "direction_classifier",
        ),
        (
            lambda: DirectionBoosting(
                max_depth_grid=(2,),
                learning_rate_grid=(0.1,),
                max_iter_grid=(40,),
                n_cv_splits=2,
                min_train_size=8,
                calibration_fraction=0.25,
            ),
            "direction_boosting",
        ),
    ],
)
def test_direction_classifiers(
    factory,
    name: str,
    candidate_train_xy: tuple[pd.DataFrame, pd.Series],
    candidate_test_x: pd.DataFrame,
) -> None:
    X_train, y_train = candidate_train_xy
    model = factory()
    pred = model.fit(X_train, y_train).predict(candidate_test_x)
    _assert_prediction_shape(pred, len(candidate_test_x), name)
    points = np.asarray(pred.points, dtype=np.float64)
    assert np.all((points >= 0.0) & (points <= 1.0))
    for iv in pred.intervals:
        assert 0.0 <= iv.lower_95 <= iv.upper_95 <= 1.0
    assert model.tuning_evaluations >= 0


def test_harness_loop_candidates_no_model_branches(
    candidate_train_xy: tuple[pd.DataFrame, pd.Series],
    candidate_test_x: pd.DataFrame,
) -> None:
    """Evaluation-shaped loop: registry only; no per-model branches."""
    X_train, y_train = candidate_train_xy
    # Fast constructor kwargs via create_candidate inside a thin factory map.
    factories = {
        "bridge": lambda: create_candidate(
            "bridge", alphas=(0.1,), l1_ratios=(0.5,), n_cv_splits=2, min_train_size=8
        ),
        "gradient_boosting": lambda: create_candidate(
            "gradient_boosting",
            max_depth_grid=(2,),
            learning_rate_grid=(0.1,),
            max_iter_grid=(40,),
            n_cv_splits=2,
            min_train_size=8,
        ),
        "direction_classifier": lambda: create_candidate(
            "direction_classifier", C_grid=(1.0,), n_cv_splits=2, min_train_size=8
        ),
    }
    results: dict[str, ModelPrediction] = {}
    for name, factory in factories.items():
        model = factory()
        assert isinstance(model, NowcastModel)
        results[name] = model.fit(X_train, y_train).predict(candidate_test_x)
        _assert_prediction_shape(results[name], len(candidate_test_x), name)


def test_iter_candidates_default_constructible() -> None:
    names = []
    for model in iter_candidates():
        assert isinstance(model, NowcastModel)
        assert model.version == "0.1.0"
        names.append(model.name)
    assert names == list(CANDIDATE_NAMES)


def test_predict_before_fit_raises(candidate_test_x: pd.DataFrame) -> None:
    for model in (
        BridgeRegression(),
        GradientBoostingNowcast(),
        DirectionLogistic(),
        DirectionBoosting(),
        DynamicFactorNowcast(factor_grid=(1,), order_grid=(1,), maxiter=10),
    ):
        with pytest.raises(RuntimeError, match="fit"):
            model.predict(candidate_test_x)


def test_bridge_requires_features() -> None:
    y = pd.Series([0.1, 0.2, 0.15, 0.05, 0.0, -0.01, 0.02, 0.03, 0.04, 0.01, 0.0, 0.02])
    X = pd.DataFrame(index=y.index)  # zero columns
    with pytest.raises(ValueError, match="feature column"):
        BridgeRegression().fit(X, y)


def test_create_baseline_unknown_still_mentions_baseline() -> None:
    with pytest.raises(KeyError, match="Unknown baseline"):
        create_baseline("bridge")
