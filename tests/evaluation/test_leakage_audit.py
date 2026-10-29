"""Leakage audit hook tests (CI wiring)."""

from __future__ import annotations

from nowcaster.evaluation.leakage_audit import (
    randomize_as_of_map,
    run_leakage_audit_suite,
    shuffle_targets,
)
from nowcaster.evaluation.walk_forward import WalkForwardConfig, run_walk_forward
from tests.evaluation.baseline_doubles import LastValueBaseline


def test_shuffle_targets_preserves_index_destroys_order(synthetic_panel) -> None:
    _X, y, _as_of = synthetic_panel
    shuffled = shuffle_targets(y, seed=7)
    assert list(shuffled.index) == list(y.index)
    # Extremely unlikely to be identical under this seed/length.
    assert not (shuffled.to_numpy() == y.to_numpy()).all()


def test_randomize_as_of_map_jitters_dates(synthetic_panel) -> None:
    _X, _y, as_of = synthetic_panel
    jittered = randomize_as_of_map(as_of, seed=1, max_jitter_days=60)
    assert set(jittered) == set(as_of)
    assert any(jittered[k] != as_of[k] for k in as_of)


def test_leakage_audit_suite_runs(synthetic_panel) -> None:
    X, y, as_of = synthetic_panel
    cfg = WalkForwardConfig(min_train_months=12)
    reference = run_walk_forward(LastValueBaseline, X, y, as_of_by_month=as_of, config=cfg)
    suite = run_leakage_audit_suite(
        LastValueBaseline,
        X,
        y,
        as_of,
        config=cfg,
        seed=0,
        reference=reference,
    )
    assert "shuffled_targets" in suite
    assert "timing_randomize" in suite
    assert suite["timing_randomize"].passed is True
    assert suite["shuffled_targets"].metrics.n > 0
