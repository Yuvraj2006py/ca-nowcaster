"""Phase 3 gate: models evaluated; report states which beat baseline.

Evaluation Skeptic owns this gate. Modeling candidates are discovered when
registered; if none are registered the report must say so loudly and holdout
must remain locked.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from nowcaster.evaluation import (
    HOLDOUT_MONTHS,
    PHASE2_BASELINE_NAMES,
    WalkForwardConfig,
    build_synthetic_panel,
    discover_baseline_factories,
    discover_candidate_factories,
    list_expected_vs_registered,
    render_evaluation_report_markdown,
    run_leakage_audit_suite,
    run_phase3_evaluation,
    run_walk_forward,
)
from nowcaster.evaluation.holdout_lock import HoldoutLockedError
from nowcaster.evaluation.significance import bootstrap_rmse_ratio_ci, diebold_mariano

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
    # Honest-result rule visible either as a win list or a loud miss.
    assert (
        "DOES NOT BEAT" in text
        or "No Phase 3 candidate" in text
        or "No registered candidate beats" in text
        or "beat" in text.lower()
    )


def test_phase_3_holdout_log_still_documents_lock_policy() -> None:
    text = (ROOT / "docs" / "holdout_log.md").read_text(encoding="utf-8")
    assert "24" in text
    assert "once" in text.lower()
    # Until candidates are final, the log must not claim a burned final set
    # without an Evaluation unlock row — Phase 3 scaffolding may only document lock.
    assert "lock" in text.lower() or "LOCKED" in text or "not burned" in text.lower()


def test_phase_3_baselines_evaluated_with_significance() -> None:
    factories = discover_baseline_factories()
    assert factories is not None
    assert set(PHASE2_BASELINE_NAMES).issubset(factories)

    X, y, as_of = build_synthetic_panel()
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
    X, y, as_of = build_synthetic_panel()
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
    X, y, as_of = build_synthetic_panel()
    cfg = WalkForwardConfig(
        min_train_months=24,
        exclude_holdout=False,
        holdout_unlocked=False,
    )
    with pytest.raises(HoldoutLockedError):
        run_walk_forward(factories["ar1"], X, y, as_of_by_month=as_of, config=cfg)


def test_phase_3_candidate_status_and_report_pipeline() -> None:
    status = list_expected_vs_registered()
    assert "expected" in status and "missing" in status
    candidates = discover_candidate_factories()
    X, y, as_of = build_synthetic_panel()
    data = run_phase3_evaluation(
        X,
        y,
        as_of,
        panel_label="synthetic Phase 3 gate panel",
        config=WalkForwardConfig(min_train_months=24, exclude_holdout=True),
        n_bootstrap=50,
        seed=0,
    )
    md = render_evaluation_report_markdown(data)
    assert "HONEST RESULT" in md or data.honest_headline
    assert data.reference_baseline == "ar1"
    assert len(data.verdicts) >= 3
    if not candidates:
        assert not status["registered"]
        assert "not burned" in data.holdout_status.lower() or "LOCKED" in data.holdout_status
    else:
        # When Modeling registers candidates, each must appear in verdicts.
        for name in candidates:
            assert any(v.model_name == name for v in data.verdicts)


def test_phase_3_gates_md_lists_phase_3() -> None:
    text = (ROOT / "docs" / "gates.md").read_text(encoding="utf-8")
    assert "Phase 3" in text or "| 3." in text
