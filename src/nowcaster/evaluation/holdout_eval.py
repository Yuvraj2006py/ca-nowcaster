"""Locked holdout evaluation — once per final model version.

Do not call unlock paths until Modeling registers final candidate versions.
Every intentional holdout score must append a row to docs/holdout_log.md.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from nowcaster.evaluation.holdout_lock import (
    HoldoutLockedError,
    HoldoutWindow,
    resolve_holdout_window,
)
from nowcaster.evaluation.walk_forward import (
    ModelFactory,
    WalkForwardConfig,
    WalkForwardResult,
    metrics_from_folds,
    run_walk_forward,
)

DEFAULT_HOLDOUT_LOG = Path("docs/holdout_log.md")


@dataclass
class HoldoutEvalRegistry:
    """In-memory registry of (model_name, model_version) already scored on holdout.

    Inputs: optional seed set of previously logged keys.
    Outputs: guards against double-burning the same version.
    Time allowed to know: registry metadata only.
    """

    scored: set[tuple[str, str]] = field(default_factory=set)

    def already_scored(self, model_name: str, model_version: str) -> bool:
        """Return True if this exact model version already touched holdout.

        Inputs: model name and version strings.
        Outputs: bool.
        Time allowed to know: registry only.
        """
        return (model_name, model_version) in self.scored

    def register(self, model_name: str, model_version: str) -> None:
        """Record that a version has been scored (call after a successful run).

        Inputs: model name and version.
        Outputs: None; raises ValueError on duplicate.
        Time allowed to know: registry only.
        """
        key = (model_name, model_version)
        if key in self.scored:
            raise ValueError(
                f"holdout already evaluated for {model_name!r} version {model_version!r}; "
                "do not burn the locked window twice for the same version"
            )
        self.scored.add(key)


# Process-global registry for one evaluation session / CI process.
_SESSION_REGISTRY = HoldoutEvalRegistry()


def session_holdout_registry() -> HoldoutEvalRegistry:
    """Return the process-global holdout evaluation registry.

    Inputs: none.
    Outputs: HoldoutEvalRegistry singleton for this Python process.
    Time allowed to know: n/a.
    """
    return _SESSION_REGISTRY


def reset_session_holdout_registry() -> None:
    """Clear the process registry (tests only).

    Inputs: none.
    Outputs: None.
    Time allowed to know: n/a.
    """
    _SESSION_REGISTRY.scored.clear()


def format_holdout_log_row(
    *,
    actor_branch: str,
    model_name: str,
    model_version: str,
    notes: str,
    when: datetime | None = None,
) -> str:
    """Format one markdown table row for docs/holdout_log.md.

    Inputs: actor/branch, model identity, notes, optional UTC timestamp.
    Outputs: markdown table row string (no trailing newline required by caller).
    Time allowed to know: wall clock for the log stamp only (not used in scoring).
    """
    stamp = (when or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%MZ")
    model_set = f"{model_name}@{model_version}"
    safe_notes = notes.replace("|", "/")
    return f"| {stamp} | {actor_branch} | {model_set} | {safe_notes} |"


def append_holdout_log(
    log_path: Path,
    *,
    actor_branch: str,
    model_name: str,
    model_version: str,
    notes: str,
    when: datetime | None = None,
) -> str:
    """Append one evaluation row to the holdout log file.

    Inputs: path to docs/holdout_log.md; row fields.
    Outputs: the row string written.
    Time allowed to know: wall clock for the log stamp only.
    """
    row = format_holdout_log_row(
        actor_branch=actor_branch,
        model_name=model_name,
        model_version=model_version,
        notes=notes,
        when=when,
    )
    text = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    if not text.endswith("\n"):
        text += "\n"
    log_path.write_text(text + row + "\n", encoding="utf-8")
    return row


def evaluate_holdout_once(
    model_factory: ModelFactory,
    X: pd.DataFrame,
    y: pd.Series,
    *,
    as_of_by_month: Mapping[date, date] | None = None,
    config: WalkForwardConfig | None = None,
    registry: HoldoutEvalRegistry | None = None,
    actor_branch: str,
    log_path: Path | None = None,
    notes: str = "final holdout evaluation",
    write_log: bool = True,
) -> WalkForwardResult:
    """Score the locked 24-month holdout exactly once per model version.

    Unlocks holdout for this call only. Refuses a second evaluation of the same
    (name, version). Optionally appends docs/holdout_log.md.

    Inputs: model factory; feature/target frames; as_of map; actor/branch for log;
      optional registry and log path.
    Outputs: WalkForwardResult restricted to holdout folds (exclude_holdout=False,
      holdout_unlocked=True).
    Time allowed to know: same as walk_forward; holdout actuals only after release.
    """
    probe = model_factory()
    name = probe.name
    version = probe.version
    reg = registry if registry is not None else session_holdout_registry()
    if reg.already_scored(name, version):
        raise HoldoutLockedError(
            f"holdout already burned for {name}@{version}; "
            "bump model_version for a new final set or do not re-score"
        )

    base = config or WalkForwardConfig()
    unlocked = WalkForwardConfig(
        min_train_months=base.min_train_months,
        holdout_unlocked=True,
        exclude_holdout=False,
        covid_shock_months=base.covid_shock_months,
        growth_already_differenced=base.growth_already_differenced,
        score_holdout_only=True,
    )
    full = run_walk_forward(
        model_factory,
        X,
        y,
        as_of_by_month=as_of_by_month,
        config=unlocked,
    )
    holdout_folds = [f for f in full.folds if f.is_holdout]
    if not holdout_folds:
        raise HoldoutLockedError(
            "holdout unlock produced zero holdout folds "
            "(series shorter than HOLDOUT_MONTHS or empty window)"
        )

    holdout_metrics = metrics_from_folds(holdout_folds, unlocked)
    result = WalkForwardResult(
        model_name=full.model_name,
        model_version=full.model_version,
        folds=holdout_folds,
        metrics=holdout_metrics,
        holdout=full.holdout,
        config=unlocked,
        extras={
            **full.extras,
            "holdout_only": True,
            "n_holdout_folds": len(holdout_folds),
        },
    )

    if write_log:
        path = log_path if log_path is not None else DEFAULT_HOLDOUT_LOG
        append_holdout_log(
            path,
            actor_branch=actor_branch,
            model_name=name,
            model_version=version,
            notes=notes,
        )
    reg.register(name, version)
    return result


def holdout_window_for_index(index: Any) -> HoldoutWindow:
    """Resolve holdout window from a feature/target index of ref months.

    Inputs: pandas Index or sequence of dates.
    Outputs: HoldoutWindow.
    Time allowed to know: month labels only.
    """
    months: list[date] = []
    for label in index:
        if isinstance(label, date) and not isinstance(label, pd.Timestamp):
            months.append(date(label.year, label.month, 1))
        else:
            ts = pd.Timestamp(label)
            months.append(date(ts.year, ts.month, 1))
    return resolve_holdout_window(months)
