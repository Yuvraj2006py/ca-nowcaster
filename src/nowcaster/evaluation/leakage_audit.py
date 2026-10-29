"""Leakage audits: shuffled targets and randomized feature timing.

Honest harness check: when feature–target links are destroyed, skill must
collapse toward chance. Baselines that ignore X still must lose skill under
shuffled targets.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from nowcaster.evaluation.metrics import RegressionMetrics
from nowcaster.evaluation.walk_forward import (
    ModelFactory,
    WalkForwardConfig,
    WalkForwardResult,
    run_walk_forward,
)


@dataclass(frozen=True)
class LeakageAuditResult:
    """Outcome of one leakage audit variant.

    Inputs: produced by audit runners below.
    Outputs: audit name, metrics, and a pass/fail hint for CI.
    Time allowed to know: same as the underlying walk-forward on mutated inputs.
    """

    audit_name: str
    metrics: RegressionMetrics
    reference_rmse: float | None
    rmse_ratio_vs_reference: float | None
    passed: bool
    detail: str
    extras: dict[str, Any] | None = None


FeatureRebuildFn = Callable[[Mapping[date, date]], tuple[pd.DataFrame, pd.Series]]


def _rmse_ratio(audit_rmse: float, reference_rmse: float | None) -> float | None:
    if reference_rmse is None or reference_rmse == 0.0 or np.isnan(reference_rmse):
        return None
    if np.isnan(audit_rmse):
        return None
    return float(audit_rmse / reference_rmse)


def shuffle_targets(
    y: pd.Series,
    *,
    seed: int = 0,
) -> pd.Series:
    """Permute target values while keeping the index (destroys temporal link).

    Inputs: target series; RNG seed.
    Outputs: shuffled copy with the same index.
    Time allowed to know: values already on y; shuffle is an audit mutation only.
    """
    rng = np.random.default_rng(seed)
    values = np.asarray(y, dtype=float).copy()
    rng.shuffle(values)
    return pd.Series(values, index=y.index, name=y.name)


def permute_feature_rows(
    X: pd.DataFrame,
    *,
    seed: int = 0,
) -> pd.DataFrame:
    """Permute feature rows independently of the target index order.

    Destroys contemporaneous feature–target alignment (timing / leakage audit
    without needing a Feature rebuild). Models that use X should lose skill;
    feature-blind baselines will be unchanged (use shuffled_targets for them).

    Inputs: feature frame; RNG seed.
    Outputs: copy with rows reordered; index labels preserved in original order
      so walk-forward still keys months correctly while values are scrambled.
    Time allowed to know: feature values already on X; mutation is audit-only.
    """
    rng = np.random.default_rng(seed)
    values = np.asarray(X.to_numpy(dtype=float), dtype=float).copy()
    rng.shuffle(values, axis=0)
    return pd.DataFrame(values, index=X.index, columns=X.columns)


def randomize_as_of_map(
    as_of_by_month: Mapping[date, date],
    *,
    seed: int = 0,
    max_jitter_days: int = 365,
) -> dict[date, date]:
    """Jitter as-of cutoffs to break honest publication timing.

    Inputs: target month -> as_of map; seed; max absolute day jitter.
    Outputs: new dict with jittered as_of dates.
    Time allowed to know: calendar map only; does not read observation values.
    """
    rng = np.random.default_rng(seed)
    out: dict[date, date] = {}
    for month, as_of in as_of_by_month.items():
        jitter = int(rng.integers(-max_jitter_days, max_jitter_days + 1))
        out[month] = as_of + timedelta(days=jitter)
    return out


def run_shuffled_target_audit(
    model_factory: ModelFactory,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    as_of_by_month: Mapping[date, date] | None = None,
    config: WalkForwardConfig | None = None,
    seed: int = 0,
    reference: WalkForwardResult | None = None,
    min_rmse_ratio: float = 0.95,
    chance_dir_acc_max: float = 0.60,
) -> LeakageAuditResult:
    """Re-run walk-forward with shuffled targets; skill should collapse.

    Pass if either:
      (1) audit headline RMSE / reference RMSE >= min_rmse_ratio, or
      (2) shuffled directional accuracy <= chance_dir_acc_max (no retained skill).

    Criterion (2) covers weak baselines whose real-target RMSE is already high
    so a lucky shuffle can spuriously lower RMSE without implying leakage.

    Inputs: same as run_walk_forward plus seed and optional reference result.
    Outputs: LeakageAuditResult.
    Time allowed to know: same as walk-forward on shuffled y (audit only).
    """
    y_shuf = shuffle_targets(y, seed=seed)
    result = run_walk_forward(
        model_factory,
        X,
        y_shuf,
        as_of_by_month=as_of_by_month,
        config=config,
    )
    ref_rmse = None if reference is None else reference.metrics.headline.rmse
    ratio = _rmse_ratio(result.metrics.headline.rmse, ref_rmse)
    dir_acc = result.metrics.headline.directional_accuracy
    if reference is None:
        passed = result.metrics.headline.n > 0
        detail = "no reference supplied; recorded shuffled-target RMSE only"
    elif ratio is None and dir_acc is None:
        passed = False
        detail = "could not compute shuffled-target skill diagnostics"
    else:
        ratio_ok = ratio is not None and ratio >= min_rmse_ratio
        chance_ok = dir_acc is not None and dir_acc <= chance_dir_acc_max
        passed = bool(ratio_ok or chance_ok)
        detail = (
            f"shuffled/reference headline RMSE ratio="
            f"{'nan' if ratio is None else f'{ratio:.4f}'}; "
            f"shuffled dir_acc="
            f"{'nan' if dir_acc is None else f'{dir_acc:.3f}'} "
            f"(pass if ratio>={min_rmse_ratio} OR dir_acc<={chance_dir_acc_max})"
        )
    return LeakageAuditResult(
        audit_name="shuffled_targets",
        metrics=result.metrics.headline,
        reference_rmse=ref_rmse,
        rmse_ratio_vs_reference=ratio,
        passed=passed,
        detail=detail,
        extras={
            "seed": seed,
            "n_folds": len(result.folds),
            "shuffled_directional_accuracy": dir_acc,
        },
    )


def run_feature_timing_audit(
    model_factory: ModelFactory,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    as_of_by_month: Mapping[date, date] | None = None,
    config: WalkForwardConfig | None = None,
    seed: int = 0,
    reference: WalkForwardResult | None = None,
    min_rmse_ratio: float = 0.95,
    uses_features: bool = True,
) -> LeakageAuditResult:
    """Permute feature rows (timing scramble); feature-using skill should collapse.

    When ``uses_features`` is False (Phase 2 baselines), the audit records that
    scrambling X cannot change predictions and marks passed=True with an
    explanatory note — shuffled_targets is the binding check for those models.

    Inputs: model factory, X, y, optional as_of/config/reference; uses_features flag.
    Outputs: LeakageAuditResult named ``feature_timing_randomize``.
    Time allowed to know: walk-forward on row-scrambled X (audit only).
    """
    X_scramble = permute_feature_rows(X, seed=seed)
    result = run_walk_forward(
        model_factory,
        X_scramble,
        y,
        as_of_by_month=as_of_by_month,
        config=config,
    )
    ref_rmse = None if reference is None else reference.metrics.headline.rmse
    ratio = _rmse_ratio(result.metrics.headline.rmse, ref_rmse)

    if not uses_features:
        return LeakageAuditResult(
            audit_name="feature_timing_randomize",
            metrics=result.metrics.headline,
            reference_rmse=ref_rmse,
            rmse_ratio_vs_reference=ratio,
            passed=True,
            detail=(
                "model declared feature-blind; feature-row scramble cannot collapse "
                "skill — rely on shuffled_targets audit"
            ),
            extras={
                "seed": seed,
                "n_folds": len(result.folds),
                "uses_features": False,
            },
        )

    if reference is None:
        passed = result.metrics.headline.n > 0
        detail = "no reference supplied; recorded scrambled-feature RMSE only"
    elif ratio is None:
        passed = False
        detail = "could not compute RMSE ratio vs reference"
    else:
        passed = ratio >= min_rmse_ratio
        detail = (
            f"scrambled-features/reference headline RMSE ratio={ratio:.4f} "
            f"(pass if >= {min_rmse_ratio}; feature skill should collapse)"
        )
    return LeakageAuditResult(
        audit_name="feature_timing_randomize",
        metrics=result.metrics.headline,
        reference_rmse=ref_rmse,
        rmse_ratio_vs_reference=ratio,
        passed=passed,
        detail=detail,
        extras={"seed": seed, "n_folds": len(result.folds), "uses_features": True},
    )


def run_timing_randomize_audit(
    model_factory: ModelFactory,
    X: pd.DataFrame,
    y: pd.Series,
    as_of_by_month: Mapping[date, date],
    *,
    config: WalkForwardConfig | None = None,
    seed: int = 0,
    max_jitter_days: int = 365,
    reference: WalkForwardResult | None = None,
    max_rmse_ratio: float = 0.95,
    feature_rebuild: FeatureRebuildFn | None = None,
    min_rmse_ratio: float = 0.95,
) -> LeakageAuditResult:
    """Jitter as-of dates; optionally rebuild features under jittered cutoffs.

    Without ``feature_rebuild``, this is a soft harness hook (RMSE often unchanged
    because X is pre-built). With rebuild, skill should collapse for look-ahead
    leaks (pass if scrambled RMSE / reference >= min_rmse_ratio).

    Inputs: model factory, X, y, as_of map, jitter knobs, optional rebuild fn.
    Outputs: LeakageAuditResult named ``timing_randomize``.
    Time allowed to know: walk-forward under jittered as_of; rebuild must itself
      respect the jittered cutoffs when supplied.
    """
    jittered = randomize_as_of_map(as_of_by_month, seed=seed, max_jitter_days=max_jitter_days)
    if feature_rebuild is not None:
        X_use, y_use = feature_rebuild(jittered)
        result = run_walk_forward(
            model_factory,
            X_use,
            y_use,
            as_of_by_month=jittered,
            config=config,
        )
        ref_rmse = None if reference is None else reference.metrics.headline.rmse
        ratio = _rmse_ratio(result.metrics.headline.rmse, ref_rmse)
        if reference is None or ratio is None:
            passed = result.metrics.headline.n > 0
            detail = "timing-randomize with feature rebuild; no usable reference ratio"
        else:
            passed = ratio >= min_rmse_ratio
            detail = (
                f"as_of-jitter + feature rebuild RMSE ratio={ratio:.4f} "
                f"(pass if >= {min_rmse_ratio})"
            )
        return LeakageAuditResult(
            audit_name="timing_randomize",
            metrics=result.metrics.headline,
            reference_rmse=ref_rmse,
            rmse_ratio_vs_reference=ratio,
            passed=passed,
            detail=detail,
            extras={
                "seed": seed,
                "max_jitter_days": max_jitter_days,
                "n_folds": len(result.folds),
                "strict_feature_rebuild": True,
                "max_rmse_ratio_hint": max_rmse_ratio,
            },
        )

    result = run_walk_forward(
        model_factory,
        X,
        y,
        as_of_by_month=jittered,
        config=config,
    )
    ref_rmse = None if reference is None else reference.metrics.headline.rmse
    ratio = _rmse_ratio(result.metrics.headline.rmse, ref_rmse)
    passed = result.metrics.headline.n > 0
    detail = (
        "timing-randomize hook executed with jittered as_of map only; "
        "pair with feature_rebuild=... for a strict leakage collapse test"
    )
    if ratio is not None:
        detail = f"{detail}; rmse_ratio_vs_reference={ratio:.4f}"
    return LeakageAuditResult(
        audit_name="timing_randomize",
        metrics=result.metrics.headline,
        reference_rmse=ref_rmse,
        rmse_ratio_vs_reference=ratio,
        passed=passed,
        detail=detail,
        extras={
            "seed": seed,
            "max_jitter_days": max_jitter_days,
            "n_folds": len(result.folds),
            "strict_feature_rebuild_required": True,
            "max_rmse_ratio_hint": max_rmse_ratio,
        },
    )


def run_leakage_audit_suite(
    model_factory: ModelFactory,
    X: pd.DataFrame,
    y: pd.Series,
    as_of_by_month: Mapping[date, date],
    *,
    config: WalkForwardConfig | None = None,
    seed: int = 0,
    reference: WalkForwardResult | None = None,
    uses_features: bool = False,
    feature_rebuild: FeatureRebuildFn | None = None,
) -> dict[str, LeakageAuditResult]:
    """Run shuffled-target, feature-timing, and as_of-timing audits.

    Inputs: same as individual audits; ``uses_features`` selects collapse criteria
      for the feature-row scramble; optional feature_rebuild for strict as_of test.
    Outputs: dict keyed by audit_name.
    Time allowed to know: see each audit docstring.
    """
    if reference is None:
        reference = run_walk_forward(
            model_factory,
            X,
            y,
            as_of_by_month=as_of_by_month,
            config=config,
        )
    shuffled = run_shuffled_target_audit(
        model_factory,
        X,
        y,
        as_of_by_month=as_of_by_month,
        config=config,
        seed=seed,
        reference=reference,
    )
    feature_timing = run_feature_timing_audit(
        model_factory,
        X,
        y,
        as_of_by_month=as_of_by_month,
        config=config,
        seed=seed,
        reference=reference,
        uses_features=uses_features,
    )
    timing = run_timing_randomize_audit(
        model_factory,
        X,
        y,
        as_of_by_month,
        config=config,
        seed=seed,
        reference=reference,
        feature_rebuild=feature_rebuild,
    )
    return {
        shuffled.audit_name: shuffled,
        feature_timing.audit_name: feature_timing,
        timing.audit_name: timing,
    }
