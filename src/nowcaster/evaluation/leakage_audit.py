"""Leakage audit hooks for CI (timing randomize / shuffled targets).

Phase 2 wires the hooks so DevOps can call them from CI later. They do not
emit Phase 3 verdicts; they return structured audit results that should look
like chance performance when the harness is honest.
"""

from __future__ import annotations

from collections.abc import Mapping
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

    Inputs: produced by run_timing_randomize_audit / run_shuffled_target_audit.
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


def randomize_as_of_map(
    as_of_by_month: Mapping[date, date],
    *,
    seed: int = 0,
    max_jitter_days: int = 365,
) -> dict[date, date]:
    """Jitter as-of cutoffs to break honest publication timing.

    A model that relied on look-ahead via mis-timed features would often still
    look good under mild jitter; large random jitter plus feature rebuilds (CI)
    should collapse skill. This hook randomizes the as-of map alone so CI can
    pair it with a feature rebuild later.

    Inputs: target month -> as_of map; seed; max absolute day jitter.
    Outputs: new dict with jittered as_of dates (clipped to remain date objects).
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
    max_rmse_ratio: float = 0.95,
) -> LeakageAuditResult:
    """Re-run walk-forward with shuffled targets; skill should not beat reference.

    Pass criterion (CI hint): audit headline RMSE should be *worse* (higher)
    than the reference, i.e. rmse_ratio_vs_reference >= max_rmse_ratio
    (default 0.95). If there is no reference, passed=True when n>0 only.

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
    if reference is None:
        passed = result.metrics.headline.n > 0
        detail = "no reference supplied; recorded shuffled-target RMSE only"
    elif ratio is None:
        passed = False
        detail = "could not compute RMSE ratio vs reference"
    else:
        # Shuffled targets should not retain most of the real-target skill.
        passed = ratio >= max_rmse_ratio
        detail = f"shuffled/reference headline RMSE ratio={ratio:.4f} (pass if >= {max_rmse_ratio})"
    return LeakageAuditResult(
        audit_name="shuffled_targets",
        metrics=result.metrics.headline,
        reference_rmse=ref_rmse,
        rmse_ratio_vs_reference=ratio,
        passed=passed,
        detail=detail,
        extras={"seed": seed, "n_folds": len(result.folds)},
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
) -> LeakageAuditResult:
    """Re-run walk-forward with randomized as-of dates (CI timing hook).

    Note: when X is pre-built and not rebuilt under the jittered as-of dates,
    this audit mainly checks that the harness accepts mutated timing maps.
    Full leakage force requires Feature rebuild at jittered as_of (Phase 3 CI).

    Inputs: model factory, X, y, as_of map, jitter knobs, optional reference.
    Outputs: LeakageAuditResult.
    Time allowed to know: walk-forward under jittered as_of labels; X must still
      be leakage-safe for the *original* builds unless caller rebuilds features.
    """
    jittered = randomize_as_of_map(as_of_by_month, seed=seed, max_jitter_days=max_jitter_days)
    result = run_walk_forward(
        model_factory,
        X,
        y,
        as_of_by_month=jittered,
        config=config,
    )
    ref_rmse = None if reference is None else reference.metrics.headline.rmse
    ratio = _rmse_ratio(result.metrics.headline.rmse, ref_rmse)
    # Timing-only jitter without feature rebuild often leaves RMSE unchanged;
    # hook still returns structured output for CI. Soft pass: ran successfully.
    passed = result.metrics.headline.n > 0
    detail = (
        "timing-randomize hook executed with jittered as_of map; "
        "pair with feature rebuild at jittered as_of for a strict CI leakage test"
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
) -> dict[str, LeakageAuditResult]:
    """Run shuffled-target and timing-randomize audits (CI entrypoint).

    Inputs: same as individual audits.
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
    timing = run_timing_randomize_audit(
        model_factory,
        X,
        y,
        as_of_by_month,
        config=config,
        seed=seed,
        reference=reference,
    )
    return {shuffled.audit_name: shuffled, timing.audit_name: timing}
