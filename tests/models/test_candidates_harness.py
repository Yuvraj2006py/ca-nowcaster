"""Phase 3 candidates through Evaluation's walk-forward harness (no eval edits)."""

from __future__ import annotations

import pandas as pd

from nowcaster.evaluation import WalkForwardConfig, compare_to_baselines, run_walk_forward
from nowcaster.models import create_baseline, create_candidate


def test_bridge_through_walk_forward(feature_frame: pd.DataFrame) -> None:
    """Registry factory + walk_forward + baseline comparison without model branches."""
    y = feature_frame["mom_growth"]
    X = feature_frame.drop(columns=["mom_growth"])
    cfg = WalkForwardConfig(min_train_months=12, exclude_holdout=True)

    def bridge_factory():
        return create_candidate(
            "bridge",
            alphas=(0.1,),
            l1_ratios=(0.5,),
            n_cv_splits=2,
            min_train_size=8,
        )

    candidate = run_walk_forward(bridge_factory, X, y, config=cfg)
    assert candidate.model_name == "bridge"
    assert len(candidate.folds) >= 1
    # Headline metrics exclude COVID shock months; full_sample counts all folds.
    assert candidate.metrics.full_sample.n == len(candidate.folds)
    assert candidate.metrics.headline.n <= candidate.metrics.full_sample.n

    ar1 = run_walk_forward(lambda: create_baseline("ar1"), X, y, config=cfg)
    compared = compare_to_baselines(candidate, {"ar1": ar1})
    assert compared.metrics.vs_baselines_headline
    assert compared.metrics.vs_baselines_headline[0].baseline_name == "ar1"


def test_direction_classifier_through_walk_forward(feature_frame: pd.DataFrame) -> None:
    y = feature_frame["mom_growth"]
    X = feature_frame.drop(columns=["mom_growth"])
    cfg = WalkForwardConfig(min_train_months=12, exclude_holdout=True)

    result = run_walk_forward(
        lambda: create_candidate(
            "direction_classifier",
            C_grid=(1.0,),
            n_cv_splits=2,
            min_train_size=8,
        ),
        X,
        y,
        config=cfg,
    )
    assert result.model_name == "direction_classifier"
    assert len(result.folds) >= 1
    for fold in result.folds:
        assert 0.0 <= fold.point <= 1.0
