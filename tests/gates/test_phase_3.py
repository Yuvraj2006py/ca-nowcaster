"""Phase 3 gate: models evaluated; report states which beat baseline.

Evaluation Skeptic owns this gate. Heavy candidate walk-forwards (DFM/GBM)
live in docs/evaluation_report.md — CI checks discovery, artifacts, baselines,
and report/holdout log content without re-fitting every expensive candidate.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from nowcaster.evaluation import (
    HOLDOUT_MONTHS,
    PHASE2_BASELINE_NAMES,
    PHASE3_CANDIDATE_NAMES,
    WalkForwardConfig,
    build_synthetic_panel,
    discover_baseline_factories,
    discover_candidate_factories,
    evaluate_holdout_once,
    list_expected_vs_registered,
    reset_session_holdout_registry,
    run_leakage_audit_suite,
    run_walk_forward,
)
from nowcaster.evaluation.holdout_eval import HoldoutEvalRegistry
from nowcaster.evaluation.holdout_lock import HoldoutLockedError
from nowcaster.evaluation.significance import bootstrap_rmse_ratio_ci, diebold_mariano
from nowcaster.models import create_candidate, list_candidates

ROOT = Path(__file__).resolve().parents[2]


def test_phase_3_evaluation_artifacts_exist() -> None:
    required = [
        "src/nowcaster/evaluation/significance.py",
        "src/nowcaster/evaluation/holdout_eval.py",
        "src/nowcaster/evaluation/candidates.py",
        "src/nowcaster/evaluation/report.py",
        "src/nowcaster/evaluation/metrics.py",
        "src/nowcaster/evaluation/leakage_audit.py",
        "docs/evaluation_report.md",
        "docs/holdout_log.md",
        "docs/requests/modeling-phase3-candidate-registration.md",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Phase 3 evaluation artifacts missing: {missing}"


def test_phase_3_report_has_loud_verdicts() -> None:
    text = (ROOT / "docs" / "evaluation_report.md").read_text(encoding="utf-8")
    assert "Loud verdict" in text or "HONEST RESULT" in text
    assert "Diebold-Mariano" in text or "diebold" in text.lower()
    assert "holdout" in text.lower()
    assert "baseline" in text.lower()
    assert (
        "DOES NOT BEAT" in text
        or "No Phase 3 candidate" in text
        or "No registered candidate beats" in text
        or "No regression candidate beats" in text
        or "beat" in text.lower()
    )


def test_phase_3_holdout_log_policy_and_burns() -> None:
    text = (ROOT / "docs" / "holdout_log.md").read_text(encoding="utf-8")
    assert "24" in text
    assert "once" in text.lower()
    candidates = discover_candidate_factories()
    if candidates:
        # Final versions burned once per (name, 0.1.0).
        for name in (
            "bridge",
            "dynamic_factor",
            "gradient_boosting",
            "direction_classifier",
        ):
            if name in candidates:
                assert f"{name}@0.1.0" in text, f"missing holdout burn row for {name}@0.1.0"
    else:
        assert "lock" in text.lower() or "LOCKED" in text or "not burned" in text.lower()


def test_phase_3_modeling_candidates_registered() -> None:
    status = list_expected_vs_registered()
    names = list(list_candidates())
    factories = discover_candidate_factories()
    assert set(names) == set(factories)
    # Core expected set from the registration request must be present.
    for name in ("bridge", "dynamic_factor", "gradient_boosting", "direction_classifier"):
        assert name in names
        model = create_candidate(name)
        assert model.name == name
        assert model.version == "0.1.0"
    assert not status["missing"] or set(status["missing"]) <= {"direction_boosting"}
    # direction_boosting is optional comparison; if registered, version 0.1.0.
    if "direction_boosting" in names:
        assert create_candidate("direction_boosting").version == "0.1.0"
    assert set(PHASE3_CANDIDATE_NAMES) - {"direction_boosting"} <= set(names)


def test_phase_3_baselines_evaluated_with_significance() -> None:
    factories = discover_baseline_factories()
    assert factories is not None
    assert set(PHASE2_BASELINE_NAMES).issubset(factories)

    # Short panel keeps CI fast while still covering COVID + holdout lock.
    X, y, as_of = build_synthetic_panel(start="2018-01", end="2022-12")
    cfg = WalkForwardConfig(min_train_months=24, exclude_holdout=True)
    results = {
        name: run_walk_forward(factory, X, y, as_of_by_month=as_of, config=cfg)
        for name, factory in factories.items()
    }
    for name, result in results.items():
        assert result.folds, f"{name} produced no folds"
        assert all(not f.is_holdout for f in result.folds)
        assert result.holdout.n_holdout == HOLDOUT_MONTHS
        assert result.metrics.classifier["available"] is True

    ref = results["ar1"]
    cand = results["last_value"]
    months = {f.target_ref_month for f in ref.folds if not f.is_covid_shock}
    months &= {f.target_ref_month for f in cand.folds if not f.is_covid_shock}
    shared = sorted(months)
    assert shared
    ref_map = {f.target_ref_month: f for f in ref.folds}
    cand_map = {f.target_ref_month: f for f in cand.folds}
    actual = [ref_map[m].actual for m in shared]
    dm = diebold_mariano(
        actual,
        [cand_map[m].point for m in shared],
        [ref_map[m].point for m in shared],
    )
    assert dm.n == len(shared)
    assert np.isfinite(dm.statistic) or dm.mean_loss_diff == 0.0
    ci = bootstrap_rmse_ratio_ci(
        actual,
        [cand_map[m].point for m in shared],
        [ref_map[m].point for m in shared],
        n_bootstrap=100,
        seed=0,
    )
    assert ci.n_obs == len(shared)


def test_phase_3_leakage_audits_on_baselines() -> None:
    factories = discover_baseline_factories()
    assert factories is not None
    X, y, as_of = build_synthetic_panel(start="2018-01", end="2022-12")
    cfg = WalkForwardConfig(min_train_months=24)
    suite = run_leakage_audit_suite(
        factories["last_value"],
        X,
        y,
        as_of,
        config=cfg,
        seed=1,
        uses_features=False,
    )
    assert suite["shuffled_targets"].metrics.n > 0
    assert suite["feature_timing_randomize"].passed is True
    assert suite["timing_randomize"].passed is True


def test_phase_3_holdout_remains_locked_without_unlock() -> None:
    factories = discover_baseline_factories()
    assert factories is not None
    X, y, as_of = build_synthetic_panel(start="2018-01", end="2022-12")
    cfg = WalkForwardConfig(
        min_train_months=24,
        exclude_holdout=False,
        holdout_unlocked=False,
    )
    with pytest.raises(HoldoutLockedError):
        run_walk_forward(factories["ar1"], X, y, as_of_by_month=as_of, config=cfg)


def test_phase_3_holdout_once_api_on_bridge() -> None:
    """Smoke the once-per-version holdout path on a cheapish candidate (bridge)."""
    factories = discover_candidate_factories()
    if "bridge" not in factories:
        pytest.skip("bridge candidate not registered")
    X, y, as_of = build_synthetic_panel(start="2018-01", end="2022-12")
    reset_session_holdout_registry()
    registry = HoldoutEvalRegistry()
    result = evaluate_holdout_once(
        factories["bridge"],
        X,
        y,
        as_of_by_month=as_of,
        config=WalkForwardConfig(min_train_months=24),
        registry=registry,
        actor_branch="cursor/evaluation-phase3-skeptic-8bfa",
        write_log=False,
        notes="gate smoke — no log write",
    )
    assert result.folds
    assert all(f.is_holdout for f in result.folds)
    assert result.metrics.headline.n > 0
    with pytest.raises(HoldoutLockedError):
        evaluate_holdout_once(
            factories["bridge"],
            X,
            y,
            as_of_by_month=as_of,
            config=WalkForwardConfig(min_train_months=24),
            registry=registry,
            actor_branch="cursor/evaluation-phase3-skeptic-8bfa",
            write_log=False,
        )


def test_phase_3_report_mentions_registered_candidates() -> None:
    text = (ROOT / "docs" / "evaluation_report.md").read_text(encoding="utf-8")
    for name in list_candidates():
        assert f"`{name}`" in text or name in text


def test_phase_3_gates_md_lists_phase_3() -> None:
    text = (ROOT / "docs" / "gates.md").read_text(encoding="utf-8")
    assert "Phase 3" in text or "| 3." in text
