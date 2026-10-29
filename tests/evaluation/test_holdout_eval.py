"""Holdout-once protocol tests — unlock only through evaluate_holdout_once."""

from __future__ import annotations

from pathlib import Path

import pytest

from nowcaster.evaluation.holdout_eval import (
    HoldoutEvalRegistry,
    evaluate_holdout_once,
    format_holdout_log_row,
    reset_session_holdout_registry,
)
from nowcaster.evaluation.holdout_lock import HoldoutLockedError
from nowcaster.evaluation.walk_forward import WalkForwardConfig
from tests.evaluation.baseline_doubles import LastValueBaseline


def test_format_holdout_log_row() -> None:
    row = format_holdout_log_row(
        actor_branch="cursor/evaluation-phase3-skeptic-8bfa",
        model_name="ar1",
        model_version="0.1.0",
        notes="unit test",
    )
    assert row.startswith("| ")
    assert "ar1@0.1.0" in row
    assert "unit test" in row


def test_evaluate_holdout_once_and_refuse_duplicate(synthetic_panel, tmp_path: Path) -> None:
    reset_session_holdout_registry()
    X, y, as_of = synthetic_panel
    log_path = tmp_path / "holdout_log.md"
    log_path.write_text("# Holdout log\n\n| Date | Actor | Model set | Notes |\n", encoding="utf-8")
    cfg = WalkForwardConfig(min_train_months=12)
    registry = HoldoutEvalRegistry()

    result = evaluate_holdout_once(
        LastValueBaseline,
        X,
        y,
        as_of_by_month=as_of,
        config=cfg,
        registry=registry,
        actor_branch="cursor/evaluation-phase3-skeptic-8bfa",
        log_path=log_path,
        notes="synthetic fixture once-per-version check",
    )
    assert result.folds
    assert all(f.is_holdout for f in result.folds)
    assert result.metrics.headline.n > 0
    text = log_path.read_text(encoding="utf-8")
    assert "last_value@" in text

    with pytest.raises(HoldoutLockedError):
        evaluate_holdout_once(
            LastValueBaseline,
            X,
            y,
            as_of_by_month=as_of,
            config=cfg,
            registry=registry,
            actor_branch="cursor/evaluation-phase3-skeptic-8bfa",
            log_path=log_path,
            notes="duplicate should fail",
            write_log=False,
        )
