"""Baseline registry for the evaluation harness.

Evaluation imports create_baseline / iter_baselines and runs fit/predict
through the NowcastModel protocol. Adding Phase 3 models later should extend
this module without requiring Evaluation to edit baseline class bodies.

Inputs: baseline name and optional constructor kwargs.
Outputs: unfitted NowcastModel instances.
Time allowed to know: none (constructors only; no data).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import Any

from nowcaster.contracts import NowcastModel
from nowcaster.models.baselines import AR1Baseline, LastValueBaseline, RollingMeanBaseline

BaselineFactory = Callable[..., NowcastModel]

# Stable names Evaluation can hard-code without importing class symbols.
BASELINE_FACTORIES: dict[str, BaselineFactory] = {
    LastValueBaseline.name: LastValueBaseline,
    AR1Baseline.name: AR1Baseline,
    RollingMeanBaseline.name: RollingMeanBaseline,
}

BASELINE_NAMES: tuple[str, ...] = tuple(BASELINE_FACTORIES.keys())


def list_baselines() -> list[str]:
    """Return registered Phase 2 baseline names in harness order.

    Inputs: none.
    Outputs: list of model name strings.
    Time allowed to know: none.
    """
    return list(BASELINE_NAMES)


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
