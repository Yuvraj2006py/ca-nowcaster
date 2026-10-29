"""Discover Phase 3 Modeling candidates without editing model code.

Evaluation prefers a Modeling registry API:

    from nowcaster.models import list_candidates, create_candidate

Until Modeling ships that API, discover_candidate_factories() returns {}.
Baselines remain available via baselines_loader / create_baseline.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nowcaster.contracts import NowcastModel

ModelFactory = Callable[[], NowcastModel]

# Expected Phase 3 names from the registration request (+ Modeling's comparison model).
PHASE3_CANDIDATE_NAMES: tuple[str, ...] = (
    "bridge",
    "dynamic_factor",
    "gradient_boosting",
    "direction_classifier",
    "direction_boosting",
)

PHASE3_REGRESSION_NAMES: tuple[str, ...] = (
    "bridge",
    "dynamic_factor",
    "gradient_boosting",
)

PHASE3_DIRECTION_NAMES: tuple[str, ...] = (
    "direction_classifier",
    "direction_boosting",
)


def discover_candidate_factories() -> dict[str, ModelFactory]:
    """Return name -> zero-arg factory for registered Phase 3 candidates.

    Inputs: none (imports nowcaster.models when present).
    Outputs: dict of available candidate factories (possibly empty).
    Time allowed to know: n/a (constructors only).
    """
    try:
        from nowcaster.models import create_candidate, list_candidates
    except ImportError:
        return {}

    try:
        names = list(list_candidates())
    except Exception:
        return {}

    factories: dict[str, ModelFactory] = {}
    for name in names:

        def _factory(candidate_name: str = name) -> NowcastModel:
            return create_candidate(candidate_name)

        factories[name] = _factory
    return factories


def regression_candidate_names() -> tuple[str, ...]:
    """Registered regression candidate names (prefer Modeling's export).

    Inputs: none.
    Outputs: tuple of names.
    Time allowed to know: n/a.
    """
    try:
        from nowcaster.models import REGRESSION_CANDIDATE_NAMES

        return tuple(REGRESSION_CANDIDATE_NAMES)
    except Exception:
        registered = set(discover_candidate_factories())
        return tuple(n for n in PHASE3_REGRESSION_NAMES if n in registered)


def direction_candidate_names() -> tuple[str, ...]:
    """Registered direction-classifier candidate names.

    Inputs: none.
    Outputs: tuple of names.
    Time allowed to know: n/a.
    """
    try:
        from nowcaster.models import DIRECTION_CANDIDATE_NAMES

        return tuple(DIRECTION_CANDIDATE_NAMES)
    except Exception:
        registered = set(discover_candidate_factories())
        return tuple(n for n in PHASE3_DIRECTION_NAMES if n in registered)


def list_expected_vs_registered() -> dict[str, Any]:
    """Compare expected Phase 3 names to what Modeling has registered.

    Inputs: none.
    Outputs: dict with expected, registered, missing keys.
    Time allowed to know: n/a.
    """
    registered = sorted(discover_candidate_factories())
    missing = [n for n in PHASE3_CANDIDATE_NAMES if n not in registered]
    return {
        "expected": list(PHASE3_CANDIDATE_NAMES),
        "registered": registered,
        "missing": missing,
        "regression": list(regression_candidate_names()),
        "direction": list(direction_candidate_names()),
    }
