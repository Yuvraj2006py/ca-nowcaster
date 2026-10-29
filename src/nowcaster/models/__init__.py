"""Nowcast models implementing the shared model interface.

Phase 2 exposes baselines only (last_value, ar1, rolling_mean). Phase 3
candidates (bridge, DynamicFactorMQ, boosting, classifiers) are out of scope
here until the Phase 2 gate passes.
"""

from nowcaster.models.baselines import AR1Baseline, LastValueBaseline, RollingMeanBaseline
from nowcaster.models.intervals import gaussian_intervals
from nowcaster.models.registry import (
    BASELINE_FACTORIES,
    BASELINE_NAMES,
    create_baseline,
    iter_baselines,
    list_baselines,
)

__all__ = [
    "AR1Baseline",
    "BASELINE_FACTORIES",
    "BASELINE_NAMES",
    "LastValueBaseline",
    "RollingMeanBaseline",
    "create_baseline",
    "gaussian_intervals",
    "iter_baselines",
    "list_baselines",
]
