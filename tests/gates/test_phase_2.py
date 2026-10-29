"""Phase 2 gate pieces owned by Feature Engineer.

Modeling owns baselines end-to-end; Evaluation owns the backtest harness.
This module asserts the Feature half: leakage-safe build_features + summary docs.
Coordinate remaining Phase 2 assertions via docs/requests/ if overlapping.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from nowcaster.contracts import FeatureFrameMeta, RawObservation
from nowcaster.features import FeatureRecipe, MonthlyFeatureBuilder
from nowcaster.quality.frame import observations_to_frame

ROOT = Path(__file__).resolve().parents[2]


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
    text = (ROOT / "docs/feature_summary.md").read_text(encoding="utf-8")
    assert "| name |" in text
    assert "missing_rate" in text
    assert "ragged" in text.lower() or "leave_missing" in text
