"""Leakage audit hook tests (CI wiring)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from nowcaster.contracts import ModelPrediction, PredictionIntervals
from nowcaster.evaluation.leakage_audit import (
    permute_feature_rows,
    randomize_as_of_map,
    run_feature_timing_audit,
    run_leakage_audit_suite,
    shuffle_targets,
)
from nowcaster.evaluation.walk_forward import WalkForwardConfig, run_walk_forward
from tests.evaluation.baseline_doubles import LastValueBaseline


class _FeatureUsingDouble:
    """Test double that predicts from the first feature column (uses X)."""

    name = "feature_using_double"
    version = "test-0.1"

    def __init__(self) -> None:
        self._sigma = 1.0

    def fit(self, X: pd.DataFrame, y: pd.Series) -> _FeatureUsingDouble:
        del y
        self._sigma = 0.2
        return self

    def predict(self, X: pd.DataFrame) -> ModelPrediction:
        points = np.asarray(X.iloc[:, 0], dtype=float)
        intervals = [
            PredictionIntervals(
                point=float(p),
                lower_80=float(p - 1.28 * self._sigma),
                upper_80=float(p + 1.28 * self._sigma),
                lower_95=float(p - 1.96 * self._sigma),
                upper_95=float(p + 1.96 * self._sigma),
            )
            for p in points
        ]
        return ModelPrediction(
            points=points,
            intervals=intervals,
            model_name=self.name,
            model_version=self.version,
        )


def test_shuffle_targets_preserves_index_destroys_order(synthetic_panel) -> None:
    _X, y, _as_of = synthetic_panel
    shuffled = shuffle_targets(y, seed=7)
    assert list(shuffled.index) == list(y.index)
    # Extremely unlikely to be identical under this seed/length.
    assert not (shuffled.to_numpy() == y.to_numpy()).all()


def test_randomize_as_of_map_jitters_dates(synthetic_panel) -> None:
    _X, _y, as_of = synthetic_panel
    jittered = randomize_as_of_map(as_of, seed=1, max_jitter_days=60)
    assert set(jittered) == set(as_of)
    assert any(jittered[k] != as_of[k] for k in as_of)


def test_permute_feature_rows_scrambles_values(synthetic_panel) -> None:
    X, _y, _as_of = synthetic_panel
    scrambled = permute_feature_rows(X, seed=3)
    assert list(scrambled.index) == list(X.index)
    assert not np.allclose(scrambled.to_numpy(), X.to_numpy())


def test_leakage_audit_suite_runs(synthetic_panel) -> None:
    X, y, as_of = synthetic_panel
    cfg = WalkForwardConfig(min_train_months=12)
    reference = run_walk_forward(LastValueBaseline, X, y, as_of_by_month=as_of, config=cfg)
    suite = run_leakage_audit_suite(
        LastValueBaseline,
        X,
        y,
        as_of,
        config=cfg,
        seed=0,
        reference=reference,
        uses_features=False,
    )
    assert "shuffled_targets" in suite
    assert "timing_randomize" in suite
    assert "feature_timing_randomize" in suite
    assert suite["timing_randomize"].passed is True
    assert suite["feature_timing_randomize"].passed is True
    assert suite["shuffled_targets"].metrics.n > 0


def test_feature_timing_audit_collapses_feature_using_model(synthetic_panel) -> None:
    X, y, as_of = synthetic_panel
    # Make first column a near-perfect contemporaneous signal.
    X = X.copy()
    X.iloc[:, 0] = y.to_numpy() + 0.01
    cfg = WalkForwardConfig(min_train_months=12)
    reference = run_walk_forward(_FeatureUsingDouble, X, y, as_of_by_month=as_of, config=cfg)
    audit = run_feature_timing_audit(
        _FeatureUsingDouble,
        X,
        y,
        as_of_by_month=as_of,
        config=cfg,
        seed=0,
        reference=reference,
        uses_features=True,
        min_rmse_ratio=0.95,
    )
    assert audit.rmse_ratio_vs_reference is not None
    assert audit.rmse_ratio_vs_reference >= 0.95
    assert audit.passed is True
