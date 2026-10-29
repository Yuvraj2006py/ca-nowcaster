"""Expanding-window walk-forward backtest at correct as-of dates.

Phase 2 harness: runs any NowcastModel through chronological folds, keeps the
locked holdout untouched by default, and computes headline (COVID-excluded) plus
full-sample metrics. Model verdicts belong in Phase 3 evaluation_report.md.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from nowcaster.contracts import ModelPrediction, NowcastModel, PredictionIntervals
from nowcaster.evaluation.covid import (
    DEFAULT_COVID_SHOCK_MONTHS,
    is_covid_shock_month,
    normalize_ref_month,
)
from nowcaster.evaluation.holdout_lock import (
    HoldoutLockedError,
    HoldoutWindow,
    assert_holdout_not_scored,
    resolve_holdout_window,
)
from nowcaster.evaluation.metrics import (
    BaselineRelativeMetrics,
    ClassifierMetricsStub,
    MetricBundle,
    RegressionMetrics,
    classifier_metrics_stub,
    compute_regression_metrics,
    ratio_vs_baseline,
)

ModelFactory = Callable[[], NowcastModel]


@dataclass(frozen=True)
class WalkForwardConfig:
    """Configuration for an expanding-window backtest.

    Inputs: training/holdout/COVID policy knobs.
    Outputs: immutable config consumed by run_walk_forward.
    Time allowed to know: policy only; no observation values.
    """

    min_train_months: int = 24
    holdout_unlocked: bool = False
    exclude_holdout: bool = True
    covid_shock_months: frozenset[date] = DEFAULT_COVID_SHOCK_MONTHS
    # If True, directional accuracy uses sign of MoM growth levels (default).
    growth_already_differenced: bool = True


@dataclass(frozen=True)
class FoldPrediction:
    """One out-of-sample fold result.

    Inputs: produced inside the backtest loop.
    Outputs: audit row for metrics and leakage checks.
    Time allowed to know: as_of_date is the public-knowledge cutoff for the fold;
    actual may be attached only after its release (caller responsibility).
    """

    target_ref_month: date
    as_of_date: date
    train_months: tuple[date, ...]
    actual: float
    point: float
    lower_80: float
    upper_80: float
    lower_95: float
    upper_95: float
    model_name: str
    model_version: str
    is_covid_shock: bool
    is_holdout: bool


@dataclass
class WalkForwardResult:
    """Full backtest output for one model.

    Inputs: fold predictions + metric bundles.
    Outputs: object returned to callers / Phase 2 gate / Phase 3 reports.
    Time allowed to know: whatever was attached on each FoldPrediction.
    """

    model_name: str
    model_version: str
    folds: list[FoldPrediction]
    metrics: MetricBundle
    holdout: HoldoutWindow
    config: WalkForwardConfig
    extras: dict[str, Any] = field(default_factory=dict)


def _index_to_ref_months(index: Any) -> list[date]:
    months: list[date] = []
    for label in index:
        if isinstance(label, date) and not isinstance(label, pd.Timestamp):
            months.append(normalize_ref_month(label))
        else:
            ts = pd.Timestamp(label)
            months.append(date(ts.year, ts.month, 1))
    return months


def _resolve_as_of(
    target_month: date,
    as_of_by_month: Mapping[date, date] | None,
) -> date:
    """Pick the as-of cutoff for predicting target_month.

    Default: last day of the month after target_month (typical GDP lag sketch
    for harness tests). Production callers should pass explicit as_of_by_month
    from the release calendar / quality package.
    """
    if as_of_by_month is not None:
        key = normalize_ref_month(target_month)
        if key in as_of_by_month:
            return as_of_by_month[key]
        # Allow non-normalized keys
        if target_month in as_of_by_month:
            return as_of_by_month[target_month]
        raise KeyError(f"no as_of_date for target month {target_month}")
    # Conservative placeholder: end of month+2 (StatCan monthly GDP often ~8 weeks).
    ts = pd.Timestamp(target_month) + pd.offsets.MonthEnd(0) + pd.DateOffset(months=2)
    return ts.date()


def _row_at(frame: pd.DataFrame | pd.Series, position: int) -> Any:
    if isinstance(frame, pd.Series):
        return frame.iloc[position : position + 1]
    return frame.iloc[position : position + 1]


def _points_from_prediction(pred: ModelPrediction) -> tuple[float, PredictionIntervals]:
    points = np.asarray(pred.points, dtype=float).reshape(-1)
    if points.size < 1:
        raise ValueError(f"model {pred.model_name} returned empty prediction")
    if not pred.intervals:
        raise ValueError(f"model {pred.model_name} returned no intervals")
    return float(points[0]), pred.intervals[0]


def run_walk_forward(
    model_factory: ModelFactory,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    as_of_by_month: Mapping[date, date] | None = None,
    config: WalkForwardConfig | None = None,
) -> WalkForwardResult:
    """Expanding-window walk-forward backtest.

    For each target month t (after min_train_months), fit a fresh model on all
    earlier rows and predict t. Uses only the feature row for t at predict time;
    callers must ensure X rows were built with release_timestamp <= as_of for that
    fold (Feature Engineer contract). Holdout months are skipped unless unlocked.

    Inputs:
      model_factory: zero-arg callable returning a new NowcastModel instance.
      X: feature frame indexed by target reference month (chronological).
      y: target MoM growth aligned to X.index.
      as_of_by_month: optional map target month -> public-knowledge cutoff date.
      config: WalkForwardConfig (defaults applied when None).
    Outputs: WalkForwardResult with folds and MetricBundle (headline + full).
    Time allowed to know: per fold, only information public as of that fold's
      as_of_date; training rows must themselves be leakage-safe as-of builds.
    """
    cfg = config or WalkForwardConfig()
    if not isinstance(X, pd.DataFrame):
        raise TypeError("X must be a pandas DataFrame")
    if not isinstance(y, pd.Series):
        raise TypeError("y must be a pandas Series")
    if len(X) != len(y):
        raise ValueError("X and y must have the same length")
    if len(X) == 0:
        raise ValueError("X/y must be non-empty")

    # Align on positional order; require matching index labels.
    if not X.index.equals(y.index):
        raise ValueError("X and y must share the same index")

    ref_months = _index_to_ref_months(X.index)
    holdout = resolve_holdout_window(ref_months)
    holdout_set = set(holdout.holdout_months)

    folds: list[FoldPrediction] = []
    probe = model_factory()
    model_name = probe.name
    model_version = probe.version

    for i, target_month in enumerate(ref_months):
        if i < cfg.min_train_months:
            continue
        is_holdout = target_month in holdout_set
        if is_holdout and cfg.exclude_holdout and not cfg.holdout_unlocked:
            continue
        if is_holdout and not cfg.holdout_unlocked:
            raise HoldoutLockedError(
                f"attempted to score holdout month {target_month} without unlock"
            )

        train_months = tuple(ref_months[:i])
        as_of_date = _resolve_as_of(target_month, as_of_by_month)

        X_train = X.iloc[:i]
        y_train = y.iloc[:i]
        X_test = _row_at(X, i)
        actual = float(y.iloc[i])

        model = model_factory()
        model.fit(X_train, y_train)
        prediction = model.predict(X_test)
        point, interval = _points_from_prediction(prediction)

        folds.append(
            FoldPrediction(
                target_ref_month=target_month,
                as_of_date=as_of_date,
                train_months=train_months,
                actual=actual,
                point=point,
                lower_80=interval.lower_80,
                upper_80=interval.upper_80,
                lower_95=interval.lower_95,
                upper_95=interval.upper_95,
                model_name=prediction.model_name,
                model_version=prediction.model_version,
                is_covid_shock=is_covid_shock_month(target_month, cfg.covid_shock_months),
                is_holdout=is_holdout,
            )
        )

    scored_months = [f.target_ref_month for f in folds]
    if cfg.exclude_holdout:
        assert_holdout_not_scored(scored_months, holdout, unlocked=cfg.holdout_unlocked)

    metrics = _metrics_from_folds(folds, cfg)
    return WalkForwardResult(
        model_name=model_name,
        model_version=model_version,
        folds=folds,
        metrics=metrics,
        holdout=holdout,
        config=cfg,
    )


def _metrics_from_folds(
    folds: Sequence[FoldPrediction],
    cfg: WalkForwardConfig,
) -> MetricBundle:
    full = _regression_from_folds(list(folds), cfg)
    headline_folds = [f for f in folds if not f.is_covid_shock]
    headline = _regression_from_folds(headline_folds, cfg)
    stub = classifier_metrics_stub()
    return MetricBundle(
        headline=headline,
        full_sample=full,
        vs_baselines_headline=(),
        vs_baselines_full=(),
        classifier={
            "available": stub.available,
            "note": stub.note,
            "accuracy": stub.accuracy,
            "precision": stub.precision,
            "recall": stub.recall,
            "confusion_matrix": stub.confusion_matrix,
        },
    )


def _regression_from_folds(
    folds: list[FoldPrediction],
    cfg: WalkForwardConfig,
) -> RegressionMetrics:
    if not folds:
        return RegressionMetrics(
            n=0,
            rmse=float("nan"),
            mae=float("nan"),
            directional_accuracy=None,
            coverage_80=None,
            coverage_95=None,
        )
    actual = [f.actual for f in folds]
    predicted = [f.point for f in folds]
    return compute_regression_metrics(
        actual,
        predicted,
        lower_80=[f.lower_80 for f in folds],
        upper_80=[f.upper_80 for f in folds],
        lower_95=[f.lower_95 for f in folds],
        upper_95=[f.upper_95 for f in folds],
        previous_actual=None if cfg.growth_already_differenced else None,
    )


def compare_to_baselines(
    candidate: WalkForwardResult,
    baselines: Mapping[str, WalkForwardResult],
) -> WalkForwardResult:
    """Attach RMSE/MAE ratios vs each baseline (headline and full-sample).

    Inputs: candidate WalkForwardResult; map of baseline_name -> result
      (same folds / months expected for an honest ratio).
    Outputs: new WalkForwardResult with metrics.vs_baselines_* filled.
    Time allowed to know: summary stats already on the results.
    """
    headline_rels: list[BaselineRelativeMetrics] = []
    full_rels: list[BaselineRelativeMetrics] = []
    for name, base in baselines.items():
        headline_rels.append(
            ratio_vs_baseline(candidate.metrics.headline, base.metrics.headline, name)
        )
        full_rels.append(
            ratio_vs_baseline(candidate.metrics.full_sample, base.metrics.full_sample, name)
        )
    new_metrics = MetricBundle(
        headline=candidate.metrics.headline,
        full_sample=candidate.metrics.full_sample,
        vs_baselines_headline=tuple(headline_rels),
        vs_baselines_full=tuple(full_rels),
        classifier=dict(candidate.metrics.classifier),
    )
    return WalkForwardResult(
        model_name=candidate.model_name,
        model_version=candidate.model_version,
        folds=list(candidate.folds),
        metrics=new_metrics,
        holdout=candidate.holdout,
        config=candidate.config,
        extras=dict(candidate.extras),
    )


def run_baseline_suite(
    baselines: Mapping[str, ModelFactory],
    X: pd.DataFrame,
    y: pd.Series,
    *,
    as_of_by_month: Mapping[date, date] | None = None,
    config: WalkForwardConfig | None = None,
) -> dict[str, WalkForwardResult]:
    """Run each baseline factory through the walk-forward harness.

    Inputs: name -> model_factory map; feature/target frames; optional as-of map.
    Outputs: dict of WalkForwardResult keyed by baseline name.
    Time allowed to know: same as run_walk_forward per fold.
    """
    return {
        name: run_walk_forward(
            factory,
            X,
            y,
            as_of_by_month=as_of_by_month,
            config=config,
        )
        for name, factory in baselines.items()
    }


# Re-export stub type for type checkers / docs.
__all__ = [
    "ClassifierMetricsStub",
    "FoldPrediction",
    "ModelFactory",
    "WalkForwardConfig",
    "WalkForwardResult",
    "compare_to_baselines",
    "run_baseline_suite",
    "run_walk_forward",
]
