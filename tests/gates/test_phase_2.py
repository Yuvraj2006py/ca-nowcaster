"""Phase 2 gate: Feature frame + Modeling baselines through Evaluation harness.

Feature half (PR #17): leakage-safe ``build_features`` + summary docs.
Evaluation/Modeling half (PR #18 / #16): ``create_baseline`` / ``iter_baselines``
run end-to-end through the walk-forward backtest on fixture features.

Do not edit ``src/nowcaster/features/`` or ``src/nowcaster/models/`` from this
module — import public APIs only.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nowcaster.contracts import FeatureFrameMeta, NowcastModel, RawObservation
from nowcaster.evaluation import (
    HOLDOUT_MONTHS,
    WalkForwardConfig,
    discover_baseline_factories,
    run_baseline_suite,
    run_leakage_audit_suite,
    run_walk_forward,
)
from nowcaster.evaluation.baselines_loader import (
    PHASE2_BASELINE_NAMES,
    iter_phase2_baselines,
)
from nowcaster.features import FeatureRecipe, MonthlyFeatureBuilder, mom_growth
from nowcaster.models import create_baseline, iter_baselines, list_baselines
from nowcaster.quality import as_of
from nowcaster.quality.frame import observations_to_frame

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Feature half (owned by Feature Engineer — keep in sync with PR #17)
# ---------------------------------------------------------------------------


def _feature_gate_store() -> pd.DataFrame:
    """Deterministic staggered vintages for Phase 2 feature leakage gate."""
    rows: list[RawObservation] = []
    for i in range(15):
        year = 2023 + (i // 12)
        month = (i % 12) + 1
        ref = date(year, month, 1)
        # Indicator: release day 10 next month
        ry = year + (1 if month == 12 else 0)
        rm = 1 if month == 12 else month + 1
        rows.append(
            RawObservation(
                series_id="gate_indicator",
                ref_period=ref,
                value=100.0 + i,
                release_timestamp=datetime(ry, rm, 10, 8, 0, 0),
                retrieved_at=datetime(ry, rm, 10, 9, 0, 0),
            )
        )
        # Target: release day 28 two months later
        ty = year
        tm = month + 2
        while tm > 12:
            tm -= 12
            ty += 1
        rows.append(
            RawObservation(
                series_id="ca_gdp_basic_prices",
                ref_period=ref,
                value=1000.0 + i,
                release_timestamp=datetime(ty, tm, 28, 8, 0, 0),
                retrieved_at=datetime(ty, tm, 28, 9, 0, 0),
            )
        )
    return observations_to_frame(rows)


def test_phase_2_feature_package_and_summary_exist() -> None:
    required = [
        "src/nowcaster/features/builder.py",
        "src/nowcaster/features/transforms.py",
        "src/nowcaster/features/ragged.py",
        "src/nowcaster/features/recipe.py",
        "src/nowcaster/features/summary.py",
        "docs/feature_summary.md",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Phase 2 feature artifacts missing: {missing}"


def test_phase_2_build_features_contract_and_leakage_nesting() -> None:
    """Gate: build_features returns FeatureFrameMeta; earlier as_of ⊆ later."""
    store = _feature_gate_store()
    meta_map = {
        "gate_indicator": {"source": "statcan", "target_role": "indicator"},
        "ca_gdp_basic_prices": {"source": "statcan", "target_role": "primary_target"},
    }
    builder = MonthlyFeatureBuilder(
        store,
        recipe=FeatureRecipe(ragged_strategy="leave_missing"),
        series_meta=meta_map,
    )
    early = date(2023, 8, 5)
    late = date(2024, 1, 15)
    frame_early, meta_early = builder.build_features(early)
    frame_late, meta_late = builder.build_features(late)

    assert isinstance(meta_early, FeatureFrameMeta)
    assert isinstance(meta_late, FeatureFrameMeta)
    assert meta_early.features_hash != meta_late.features_hash

    shared_index = frame_early.index.intersection(frame_late.index)
    shared_cols = frame_early.columns.intersection(frame_late.columns)
    early_a = frame_early.loc[shared_index, shared_cols]
    late_a = frame_late.loc[shared_index, shared_cols]
    known = early_a.notna()
    assert (late_a.notna() | ~known).all().all()
    pd.testing.assert_frame_equal(
        early_a.where(known),
        late_a.where(known),
        check_exact=False,
        rtol=1e-12,
    )


def test_phase_2_feature_summary_documents_columns() -> None:
    text = (ROOT / "docs" / "feature_summary.md").read_text(encoding="utf-8")
    assert "| name |" in text
    assert "missing_rate" in text
    assert "ragged" in text.lower() or "leave_missing" in text


# ---------------------------------------------------------------------------
# Evaluation / Modeling half
# ---------------------------------------------------------------------------


def _phase2_panel() -> tuple[pd.DataFrame, pd.Series, dict[date, date]]:
    """Deterministic panel long enough for min_train + COVID + holdout."""
    rng = np.random.default_rng(0)
    months = pd.period_range("2017-01", "2022-12", freq="M")
    index = pd.Index([m.to_timestamp().date() for m in months], name="ref_month")
    y_vals = rng.normal(0.1, 0.3, size=len(index))
    for i, d in enumerate(index):
        if d.year == 2020 and 3 <= d.month <= 8:
            y_vals[i] -= 2.0
    lag = np.roll(y_vals, 1)
    lag[0] = 0.0
    X = pd.DataFrame({"lag1": lag, "noise": rng.normal(0, 1, len(index))}, index=index)
    y = pd.Series(y_vals, index=index, name="gdp_mom")
    as_of_map = {
        m: (pd.Timestamp(m) + pd.offsets.MonthEnd(0) + pd.DateOffset(months=2)).date()
        for m in index
    }
    return X, y, as_of_map


def _baseline_factories() -> dict[str, object]:
    """Prefer Modeling registry; fail the gate if Phase 2 baselines are missing."""
    factories = discover_baseline_factories()
    if factories is None:
        pytest.fail(
            "Modeling baselines not importable via create_baseline/list_baselines; "
            "merge/rebase onto PR #16 (cursor/modeling-phase2-baselines-2f3c)."
        )
    missing = [n for n in PHASE2_BASELINE_NAMES if n not in factories]
    if missing:
        pytest.fail(f"Missing Phase 2 baselines: {missing}")
    return factories


def test_phase_2_evaluation_artifacts_exist() -> None:
    required = [
        "src/nowcaster/evaluation/walk_forward.py",
        "src/nowcaster/evaluation/metrics.py",
        "src/nowcaster/evaluation/leakage_audit.py",
        "src/nowcaster/evaluation/holdout_lock.py",
        "src/nowcaster/evaluation/covid.py",
        "src/nowcaster/evaluation/baselines_loader.py",
        "docs/evaluation_phase2.md",
        "docs/holdout_log.md",
        "src/nowcaster/models/registry.py",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, f"Phase 2 evaluation artifacts missing: {missing}"


def test_phase_2_modeling_registry_api() -> None:
    names = list_baselines()
    assert set(PHASE2_BASELINE_NAMES).issubset(set(names))
    for name in PHASE2_BASELINE_NAMES:
        model = create_baseline(name)
        assert isinstance(model, NowcastModel)
        assert model.name == name
    iterated = list(iter_baselines(PHASE2_BASELINE_NAMES))
    assert [m.name for m in iterated] == list(PHASE2_BASELINE_NAMES)
    assert [m.name for m in iter_phase2_baselines()] == list(PHASE2_BASELINE_NAMES)


def test_phase_2_baselines_run_end_to_end_through_backtest() -> None:
    """Gate: three Modeling baselines complete walk-forward without scoring holdout."""
    X, y, as_of_map = _phase2_panel()
    factories = _baseline_factories()
    assert set(factories) >= set(PHASE2_BASELINE_NAMES)

    cfg = WalkForwardConfig(min_train_months=24, exclude_holdout=True)
    results = run_baseline_suite(factories, X, y, as_of_by_month=as_of_map, config=cfg)

    assert set(results) >= set(PHASE2_BASELINE_NAMES)
    for name, result in results.items():
        assert result.folds, f"{name} produced no OOS folds"
        assert all(not f.is_holdout for f in result.folds), f"{name} scored holdout"
        assert result.holdout.n_holdout == HOLDOUT_MONTHS
        assert result.metrics.full_sample.n >= result.metrics.headline.n
        assert result.metrics.headline.n > 0
        assert result.metrics.full_sample.rmse >= 0
        assert result.metrics.classifier["available"] is False
        for fold in result.folds:
            assert isinstance(fold.as_of_date, date)
            assert fold.as_of_date >= fold.target_ref_month


def test_phase_2_leakage_audit_hooks_wired() -> None:
    X, y, as_of_map = _phase2_panel()
    factories = _baseline_factories()
    cfg = WalkForwardConfig(min_train_months=24)
    suite = run_leakage_audit_suite(
        factories["last_value"],
        X,
        y,
        as_of_map,
        config=cfg,
        seed=1,
    )
    assert suite["shuffled_targets"].metrics.n > 0
    assert suite["timing_randomize"].passed is True


def test_phase_2_holdout_log_documents_lock() -> None:
    text = (ROOT / "docs" / "holdout_log.md").read_text(encoding="utf-8")
    assert "24" in text
    assert "do not burn" in text.lower()
    assert "Phase 2" in text


def test_phase_2_docs_note_phase_3_report() -> None:
    text = (ROOT / "docs" / "evaluation_phase2.md").read_text(encoding="utf-8")
    assert "evaluation_report.md" in text
    assert "Phase 3" in text
    assert "create_baseline" in text


@pytest.mark.parametrize("key", list(PHASE2_BASELINE_NAMES))
def test_phase_2_each_baseline_factory_callable(key: str) -> None:
    factories = _baseline_factories()
    model = factories[key]()
    assert model.name == key
    assert model.version


# ---------------------------------------------------------------------------
# Joint end-to-end: Feature build_features → Modeling baselines → harness
# ---------------------------------------------------------------------------


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def _joint_feature_store(*, n_months: int = 72) -> pd.DataFrame:
    """Long staggered vintage store so holdout + min_train still leave OOS folds."""
    rows: list[RawObservation] = []
    year, month = 2017, 1
    for i in range(n_months):
        ref = date(year, month, 1)
        iy, im = _add_months(year, month, 1)
        rows.append(
            RawObservation(
                series_id="gate_indicator",
                ref_period=ref,
                value=100.0 + i + 0.1 * np.sin(i / 3.0),
                release_timestamp=datetime(iy, im, 10, 8, 0, 0),
                retrieved_at=datetime(iy, im, 10, 9, 0, 0),
            )
        )
        ty, tm = _add_months(year, month, 2)
        rows.append(
            RawObservation(
                series_id="ca_gdp_basic_prices",
                ref_period=ref,
                value=1000.0 + i + 0.05 * i,
                release_timestamp=datetime(ty, tm, 28, 8, 0, 0),
                retrieved_at=datetime(ty, tm, 28, 9, 0, 0),
            )
        )
        year, month = _add_months(year, month, 1)
    return observations_to_frame(rows)


def _target_mom_from_store(store: pd.DataFrame, as_of_date: date, target_id: str) -> pd.Series:
    """MoM growth of the primary target from an as_of-filtered levels panel.

    Inputs: raw store; as_of cutoff; target series id.
    Outputs: Series indexed by Period[M] (aligned to feature frame index).
    Time allowed to know: only release_timestamp <= as_of_date (via quality.as_of).
    """
    view = as_of(store, as_of_date)
    frame = view.loc[view["series_id"].astype(str) == target_id].copy()
    if frame.empty:
        return pd.Series(dtype=float)
    frame["ref_month"] = pd.PeriodIndex(pd.to_datetime(frame["ref_period"]), freq="M")
    levels = frame.pivot_table(
        index="ref_month", columns="series_id", values="value", aggfunc="last"
    )
    levels = levels.sort_index()
    full_index = pd.period_range(levels.index.min(), levels.index.max(), freq="M")
    levels = levels.reindex(full_index)
    return mom_growth(levels[target_id]).rename("gdp_mom")


def test_phase_2_baselines_on_build_features_end_to_end() -> None:
    """Joint gate: MonthlyFeatureBuilder features → baselines → walk-forward."""
    store = _joint_feature_store()
    meta_map = {
        "gate_indicator": {"source": "statcan", "target_role": "indicator"},
        "ca_gdp_basic_prices": {"source": "statcan", "target_role": "primary_target"},
    }
    # Final as_of after the last GDP vintage in the fixture (~end of sample + 2m).
    as_of_date = date(2023, 2, 28)
    builder = MonthlyFeatureBuilder(
        store,
        recipe=FeatureRecipe(ragged_strategy="leave_missing"),
        series_meta=meta_map,
    )
    X, meta = builder.build_features(as_of_date)
    assert isinstance(meta, FeatureFrameMeta)
    assert meta.features_hash
    assert len(X.columns) > 0

    y = _target_mom_from_store(store, as_of_date, "ca_gdp_basic_prices")
    shared = X.index.intersection(y.dropna().index)
    X_aligned = X.loc[shared]
    y_aligned = y.loc[shared].astype(float)
    # Drop early warmup rows with all-NaN feature columns if any remain.
    usable = X_aligned.notna().any(axis=1) & y_aligned.notna()
    X_aligned = X_aligned.loc[usable]
    y_aligned = y_aligned.loc[usable]
    assert len(X_aligned) >= HOLDOUT_MONTHS + 12, (
        f"need history for holdout+train; got {len(X_aligned)}"
    )

    as_of_by_month = {
        (d.to_timestamp().date() if hasattr(d, "to_timestamp") else pd.Timestamp(d).date()): (
            as_of_date
        )
        for d in X_aligned.index
    }
    # Rebuild index labels as dates for harness as_of map keys used inside folds.
    date_index = pd.Index(
        [
            d.to_timestamp().date() if hasattr(d, "to_timestamp") else pd.Timestamp(d).date()
            for d in X_aligned.index
        ],
        name="ref_month",
    )
    X_dates = X_aligned.copy()
    X_dates.index = date_index
    y_dates = pd.Series(y_aligned.to_numpy(), index=date_index, name="gdp_mom")

    factories = _baseline_factories()
    cfg = WalkForwardConfig(min_train_months=12, exclude_holdout=True)
    results = run_baseline_suite(
        factories, X_dates, y_dates, as_of_by_month=as_of_by_month, config=cfg
    )

    assert set(results) >= set(PHASE2_BASELINE_NAMES)
    for name, result in results.items():
        assert result.folds, f"{name} produced no OOS folds on build_features output"
        assert all(not f.is_holdout for f in result.folds)
        assert result.metrics.headline.n > 0
        assert np.isfinite(result.metrics.full_sample.rmse)

    # At least one baseline completes a named walk-forward (Feature request #3).
    single = run_walk_forward(
        factories["last_value"],
        X_dates,
        y_dates,
        as_of_by_month=as_of_by_month,
        config=cfg,
    )
    assert single.model_name == "last_value"
    assert len(single.folds) > 0
