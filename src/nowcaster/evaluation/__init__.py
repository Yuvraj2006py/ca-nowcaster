"""Walk-forward evaluation harness and skeptic audits.

Phase 2: harness + metrics scaffolding + leakage hooks + holdout lock.
Phase 3: full model verdicts in docs/evaluation_report.md (not produced here).
"""

from nowcaster.evaluation.baselines_loader import (
    PHASE2_BASELINE_NAMES,
    discover_baseline_factories,
    iter_phase2_baselines,
)
from nowcaster.evaluation.covid import DEFAULT_COVID_SHOCK_MONTHS, is_covid_shock_month
from nowcaster.evaluation.holdout_lock import (
    HOLDOUT_MONTHS,
    HoldoutLockedError,
    HoldoutWindow,
    assert_holdout_not_scored,
    resolve_holdout_window,
)
from nowcaster.evaluation.leakage_audit import (
    LeakageAuditResult,
    randomize_as_of_map,
    run_leakage_audit_suite,
    run_shuffled_target_audit,
    run_timing_randomize_audit,
    shuffle_targets,
)
from nowcaster.evaluation.metrics import (
    BaselineRelativeMetrics,
    ClassifierMetricsStub,
    MetricBundle,
    RegressionMetrics,
    classifier_metrics_stub,
    compute_regression_metrics,
    mae,
    ratio_vs_baseline,
    rmse,
)
from nowcaster.evaluation.walk_forward import (
    FoldPrediction,
    WalkForwardConfig,
    WalkForwardResult,
    compare_to_baselines,
    run_baseline_suite,
    run_walk_forward,
)

__all__ = [
    "DEFAULT_COVID_SHOCK_MONTHS",
    "HOLDOUT_MONTHS",
    "PHASE2_BASELINE_NAMES",
    "BaselineRelativeMetrics",
    "ClassifierMetricsStub",
    "FoldPrediction",
    "HoldoutLockedError",
    "HoldoutWindow",
    "LeakageAuditResult",
    "MetricBundle",
    "RegressionMetrics",
    "WalkForwardConfig",
    "WalkForwardResult",
    "assert_holdout_not_scored",
    "classifier_metrics_stub",
    "compare_to_baselines",
    "compute_regression_metrics",
    "discover_baseline_factories",
    "is_covid_shock_month",
    "iter_phase2_baselines",
    "mae",
    "randomize_as_of_map",
    "ratio_vs_baseline",
    "resolve_holdout_window",
    "rmse",
    "run_baseline_suite",
    "run_leakage_audit_suite",
    "run_shuffled_target_audit",
    "run_timing_randomize_audit",
    "run_walk_forward",
    "shuffle_targets",
]
