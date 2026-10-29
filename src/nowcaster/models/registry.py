"""Model registry for baselines and Phase 3 candidates.

Evaluation imports create_baseline / iter_baselines (Phase 2) and
create_candidate / iter_candidates / create_model / iter_models (Phase 3)
and runs fit/predict through the NowcastModel protocol — no per-model
branches in the harness.

Inputs: model name and optional constructor kwargs.
Outputs: unfitted NowcastModel instances.
Time allowed to know: none (constructors only; no data).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from nowcaster.contracts import NowcastModel
from nowcaster.models.baselines import AR1Baseline, LastValueBaseline, RollingMeanBaseline
from nowcaster.models.boosting import GradientBoostingNowcast
from nowcaster.models.bridge import BridgeRegression
from nowcaster.models.classifiers import DirectionBoosting, DirectionLogistic
from nowcaster.models.dynamic_factor import DynamicFactorNowcast

BaselineFactory = Callable[..., NowcastModel]
ModelFactory = Callable[..., NowcastModel]

# Stable names Evaluation can hard-code without importing class symbols.
BASELINE_FACTORIES: dict[str, BaselineFactory] = {
    LastValueBaseline.name: LastValueBaseline,
    AR1Baseline.name: AR1Baseline,
    RollingMeanBaseline.name: RollingMeanBaseline,
}

BASELINE_NAMES: tuple[str, ...] = tuple(BASELINE_FACTORIES.keys())

# Phase 3 candidates (regression + direction classifiers).
CANDIDATE_FACTORIES: dict[str, ModelFactory] = {
    BridgeRegression.name: BridgeRegression,
    DynamicFactorNowcast.name: DynamicFactorNowcast,
    GradientBoostingNowcast.name: GradientBoostingNowcast,
    DirectionLogistic.name: DirectionLogistic,
    DirectionBoosting.name: DirectionBoosting,
}

CANDIDATE_NAMES: tuple[str, ...] = tuple(CANDIDATE_FACTORIES.keys())

# Regression candidates only (exclude direction classifiers).
REGRESSION_CANDIDATE_NAMES: tuple[str, ...] = (
    BridgeRegression.name,
    DynamicFactorNowcast.name,
    GradientBoostingNowcast.name,
)

DIRECTION_CANDIDATE_NAMES: tuple[str, ...] = (
    DirectionLogistic.name,  # "direction_classifier"
    DirectionBoosting.name,  # "direction_boosting" (comparison)
)

# Names Evaluation's Phase 3 gate expects (see modeling-phase3-candidate-registration).
PHASE3_EXPECTED_NAMES: tuple[str, ...] = (
    BridgeRegression.name,
    DynamicFactorNowcast.name,
    GradientBoostingNowcast.name,
    DirectionLogistic.name,
)

# Unified registry: baselines first, then candidates (stable harness order).
MODEL_FACTORIES: dict[str, ModelFactory] = {
    **BASELINE_FACTORIES,
    **CANDIDATE_FACTORIES,
}

MODEL_NAMES: tuple[str, ...] = tuple(MODEL_FACTORIES.keys())


def list_baselines() -> list[str]:
    """Return registered Phase 2 baseline names in harness order.

    Inputs: none.
    Outputs: list of model name strings.
    Time allowed to know: none.
    """
    return list(BASELINE_NAMES)


def list_candidates() -> list[str]:
    """Return registered Phase 3 candidate names in harness order.

    Inputs: none.
    Outputs: list of candidate name strings (regression + direction).
    Time allowed to know: none.
    """
    return list(CANDIDATE_NAMES)


def list_models() -> list[str]:
    """Return all registered model names (baselines then candidates).

    Inputs: none.
    Outputs: list of name strings.
    Time allowed to know: none.
    """
    return list(MODEL_NAMES)


def create_baseline(name: str, **kwargs: Any) -> NowcastModel:
    """Construct an unfitted baseline by registry name.

    Inputs: name in BASELINE_NAMES; kwargs forwarded to the constructor
            (e.g. window= for rolling_mean).
    Outputs: unfitted NowcastModel.
    Time allowed to know: none.
    """
    try:
        factory = BASELINE_FACTORIES[name]
    except KeyError as exc:
        known = ", ".join(BASELINE_NAMES)
        raise KeyError(f"Unknown baseline {name!r}; known: {known}") from exc
    return factory(**kwargs)


def create_candidate(name: str, **kwargs: Any) -> NowcastModel:
    """Construct an unfitted Phase 3 candidate by registry name.

    Inputs: name in CANDIDATE_NAMES; kwargs forwarded to the constructor.
    Outputs: unfitted NowcastModel.
    Time allowed to know: none.
    """
    try:
        factory = CANDIDATE_FACTORIES[name]
    except KeyError as exc:
        known = ", ".join(CANDIDATE_NAMES)
        raise KeyError(f"Unknown candidate {name!r}; known: {known}") from exc
    return factory(**kwargs)


def create_model(name: str, **kwargs: Any) -> NowcastModel:
    """Construct any registered model (baseline or candidate) by name.

    Inputs: name in MODEL_NAMES; kwargs forwarded to the constructor.
    Outputs: unfitted NowcastModel.
    Time allowed to know: none.
    """
    try:
        factory = MODEL_FACTORIES[name]
    except KeyError as exc:
        known = ", ".join(MODEL_NAMES)
        raise KeyError(f"Unknown model {name!r}; known: {known}") from exc
    return factory(**kwargs)


def iter_baselines(
    names: Iterable[str] | None = None,
    **kwargs: Any,
) -> Iterator[NowcastModel]:
    """Yield fresh unfitted baselines for walk-forward evaluation.

    Inputs: optional subset of names (default: all Phase 2 baselines);
            kwargs applied only where the constructor accepts them — callers
            that need per-model kwargs should call create_baseline instead.
    Outputs: iterator of unfitted models.
    Time allowed to know: none.
    """
    selected = list(names) if names is not None else list(BASELINE_NAMES)
    for name in selected:
        if name == RollingMeanBaseline.name and "window" in kwargs:
            yield create_baseline(name, window=kwargs["window"])
        else:
            yield create_baseline(name)


def iter_candidates(
    names: Iterable[str] | None = None,
    **kwargs: Any,
) -> Iterator[NowcastModel]:
    """Yield fresh unfitted Phase 3 candidates for the evaluation harness.

    Inputs: optional subset of names (default: all candidates); kwargs are
            ignored here — use create_candidate for per-model constructor args.
    Outputs: iterator of unfitted NowcastModel instances.
    Time allowed to know: none.
    """
    del kwargs  # per-model kwargs via create_candidate
    selected = list(names) if names is not None else list(CANDIDATE_NAMES)
    for name in selected:
        yield create_candidate(name)


def iter_models(
    names: Iterable[str] | None = None,
    **kwargs: Any,
) -> Iterator[NowcastModel]:
    """Yield fresh unfitted models from the unified registry.

    Inputs: optional subset of names (default: all models).
    Outputs: iterator of unfitted NowcastModel instances.
    Time allowed to know: none.
    """
    del kwargs
    selected = list(names) if names is not None else list(MODEL_NAMES)
    for name in selected:
        yield create_model(name)
