"""Load Modeling baselines via create_baseline / iter_baselines.

Evaluation must not own baseline implementations. Prefer the Modeling registry
API from PR #16:

    from nowcaster.models import create_baseline, iter_baselines

Falls back to None when models are not importable so unit tests can still use
protocol doubles before Modeling lands on main.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nowcaster.contracts import NowcastModel

ModelFactory = Callable[[], NowcastModel]

PHASE2_BASELINE_NAMES: tuple[str, ...] = ("last_value", "ar1", "rolling_mean")


def discover_baseline_factories() -> dict[str, ModelFactory] | None:
    """Return name -> zero-arg factory using Modeling's registry API.

    Inputs: none (imports nowcaster.models).
    Outputs: dict for last_value / ar1 / rolling_mean, or None if unavailable.
    Time allowed to know: n/a (constructors only; no observation values).
    """
    try:
        from nowcaster.models import create_baseline, list_baselines
    except ImportError:
        return None

    try:
        available = set(list_baselines())
    except Exception:
        return None

    if not set(PHASE2_BASELINE_NAMES).issubset(available):
        return None

    factories: dict[str, ModelFactory] = {}
    for name in PHASE2_BASELINE_NAMES:

        def _factory(baseline_name: str = name) -> NowcastModel:
            return create_baseline(baseline_name)

        factories[name] = _factory
    return factories


def iter_phase2_baselines(**kwargs: Any) -> list[NowcastModel]:
    """Materialize fresh Phase 2 baselines via Modeling's iter_baselines.

    Inputs: optional kwargs forwarded to iter_baselines (e.g. window=).
    Outputs: list of unfitted NowcastModel instances in harness order.
    Time allowed to know: none (constructors only).
    """
    from nowcaster.models import iter_baselines

    return list(iter_baselines(PHASE2_BASELINE_NAMES, **kwargs))
