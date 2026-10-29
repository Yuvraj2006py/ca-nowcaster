"""Nowcast models implementing the shared model interface.

Phase 2: baselines (last_value, ar1, rolling_mean).
Phase 3: candidates (bridge, dynamic_factor, gradient_boosting,
direction_classifier, direction_boosting).

Evaluation should import registry helpers and call fit/predict only — no
per-model branches in the harness.
"""

from nowcaster.models.baselines import AR1Baseline, LastValueBaseline, RollingMeanBaseline
from nowcaster.models.boosting import GradientBoostingNowcast
from nowcaster.models.bridge import BridgeRegression
from nowcaster.models.classifiers import DirectionBoosting, DirectionLogistic
from nowcaster.models.dynamic_factor import DynamicFactorNowcast
from nowcaster.models.intervals import conformal_intervals, gaussian_intervals
from nowcaster.models.registry import (
    BASELINE_FACTORIES,
    BASELINE_NAMES,
    CANDIDATE_FACTORIES,
    CANDIDATE_NAMES,
    DIRECTION_CANDIDATE_NAMES,
    MODEL_FACTORIES,
    MODEL_NAMES,
    PHASE3_EXPECTED_NAMES,
    REGRESSION_CANDIDATE_NAMES,
    create_baseline,
    create_candidate,
    create_model,
    iter_baselines,
    iter_candidates,
    iter_models,
    list_baselines,
    list_candidates,
    list_models,
)

__all__ = [
    "AR1Baseline",
    "BASELINE_FACTORIES",
    "BASELINE_NAMES",
    "BridgeRegression",
    "CANDIDATE_FACTORIES",
    "CANDIDATE_NAMES",
    "DIRECTION_CANDIDATE_NAMES",
    "DirectionBoosting",
    "DirectionLogistic",
    "DynamicFactorNowcast",
    "GradientBoostingNowcast",
    "LastValueBaseline",
    "MODEL_FACTORIES",
    "MODEL_NAMES",
    "PHASE3_EXPECTED_NAMES",
    "REGRESSION_CANDIDATE_NAMES",
    "RollingMeanBaseline",
    "conformal_intervals",
    "create_baseline",
    "create_candidate",
    "create_model",
    "gaussian_intervals",
    "iter_baselines",
    "iter_candidates",
    "iter_models",
    "list_baselines",
    "list_candidates",
    "list_models",
]
