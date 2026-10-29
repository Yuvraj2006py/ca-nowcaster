"""Training-window hyperparameter tuning helpers.

All grids and CV folds operate only on rows passed to ``fit``. Nothing from
the evaluation test fold may enter these routines.

Inputs: training feature/target arrays and a discrete search space.
Outputs: best params plus an integer count of (candidate, fold) evaluations.
Time allowed to know: training window only.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.model_selection import TimeSeriesSplit


@dataclass
class TuningResult:
    """Outcome of a training-window hyperparameter search.

    Inputs: produced by ``grid_search_timeseries``.
    Outputs: best kwargs, score, and evaluation count for logging.
    Time allowed to know: training window only.
    """

    best_params: dict[str, Any]
    best_score: float
    n_evaluations: int
    n_folds: int
    scored: list[dict[str, Any]] = field(default_factory=list)


def expanding_time_splits(
    n_samples: int,
    *,
    n_splits: int = 3,
    min_train_size: int = 12,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Build expanding-window train/validation index pairs inside the fit window.

    Inputs: training length; desired split count; minimum train size per fold.
    Outputs: list of (train_idx, val_idx) arrays in chronological order.
    Time allowed to know: lengths only (no values).
    """
    if n_samples < min_train_size + 1:
        return []
    max_splits = max(1, n_samples - min_train_size)
    splits = min(n_splits, max_splits)
    if splits < 1:
        return []
    cv = TimeSeriesSplit(n_splits=splits)
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for train_idx, val_idx in cv.split(np.arange(n_samples)):
        if train_idx.size < min_train_size or val_idx.size < 1:
            continue
        pairs.append((train_idx, val_idx))
    return pairs


ScoreFn = Callable[
    [Mapping[str, Any], np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    float,
]


def grid_search_timeseries(
    param_grid: Sequence[Mapping[str, Any]],
    *,
    X: np.ndarray,
    y: np.ndarray,
    fit_predict_score: ScoreFn,
    n_splits: int = 3,
    min_train_size: int = 12,
    higher_is_better: bool = False,
) -> TuningResult:
    """Exhaustive grid search with expanding-window CV on the training set.

    Inputs: discrete param dicts; training X/y; scorer(params, X_tr, y_tr, X_va, y_va)
            returning a scalar (RMSE by default — lower better).
    Outputs: TuningResult with best params and ``n_evaluations`` logged.
    Time allowed to know: training X/y only.
    """
    if not param_grid:
        raise ValueError("param_grid must be non-empty")

    folds = expanding_time_splits(X.shape[0], n_splits=n_splits, min_train_size=min_train_size)
    if not folds:
        # Too little history for CV: take the first grid point, count 0 CV evals.
        first = dict(param_grid[0])
        return TuningResult(
            best_params=first,
            best_score=float("nan"),
            n_evaluations=0,
            n_folds=0,
            scored=[{"params": first, "score": float("nan"), "note": "insufficient_history"}],
        )

    scored: list[dict[str, Any]] = []
    n_evaluations = 0
    best_params = dict(param_grid[0])
    best_score = float("-inf") if higher_is_better else float("inf")

    for params in param_grid:
        fold_scores: list[float] = []
        for train_idx, val_idx in folds:
            score = fit_predict_score(
                params,
                X[train_idx],
                y[train_idx],
                X[val_idx],
                y[val_idx],
            )
            n_evaluations += 1
            if np.isfinite(score):
                fold_scores.append(float(score))
        mean_score = float(np.mean(fold_scores)) if fold_scores else float("nan")
        scored.append({"params": dict(params), "score": mean_score, "n_folds": len(fold_scores)})
        if not np.isfinite(mean_score):
            continue
        better = mean_score > best_score if higher_is_better else mean_score < best_score
        if better:
            best_score = mean_score
            best_params = dict(params)

    return TuningResult(
        best_params=best_params,
        best_score=best_score,
        n_evaluations=n_evaluations,
        n_folds=len(folds),
        scored=scored,
    )
