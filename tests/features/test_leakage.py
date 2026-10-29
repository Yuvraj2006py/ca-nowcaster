"""Leakage tests: earlier as_of removes information, never adds it."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from nowcaster.features import FeatureRecipe, MonthlyFeatureBuilder, RaggedEdgeStrategy


@pytest.fixture
def leave_missing_builder(
    feature_store: pd.DataFrame,
    series_meta: dict[str, dict[str, str]],
) -> MonthlyFeatureBuilder:
    recipe = FeatureRecipe(ragged_strategy=RaggedEdgeStrategy.LEAVE_MISSING.value)
    return MonthlyFeatureBuilder(feature_store, recipe=recipe, series_meta=series_meta)


def test_earlier_as_of_never_adds_information(
    leave_missing_builder: MonthlyFeatureBuilder,
) -> None:
    """Shifting as_of earlier removes info: non-null early ⊆ non-null late.

    For leave_missing, every finite cell at the earlier cutoff must remain
    finite and equal at the later cutoff (nested information sets).
    """
    early = date(2024, 3, 10)
    late = date(2024, 6, 15)
    frame_early, meta_early = leave_missing_builder.build_features(early)
    frame_late, meta_late = leave_missing_builder.build_features(late)

    assert meta_early.as_of_date == early
    assert meta_late.as_of_date == late
    assert meta_early.features_hash != meta_late.features_hash

    # Align on shared index/columns.
    shared_index = frame_early.index.intersection(frame_late.index)
    shared_cols = frame_early.columns.intersection(frame_late.columns)
    early_aligned = frame_early.loc[shared_index, shared_cols]
    late_aligned = frame_late.loc[shared_index, shared_cols]

    early_known = early_aligned.notna()
    # Wherever early knows a value, late must know it too.
    assert (late_aligned.notna() | ~early_known).all().all()

    # And the values must match (no revision sneak-in for leave_missing levels path
    # when vintages are unique per ref_period in this fixture).
    early_vals = early_aligned.where(early_known)
    late_vals = late_aligned.where(early_known)
    pd.testing.assert_frame_equal(early_vals, late_vals, check_exact=False, rtol=1e-12)


def test_earlier_as_of_has_weakly_fewer_known_cells(
    leave_missing_builder: MonthlyFeatureBuilder,
) -> None:
    early = date(2024, 2, 15)
    late = date(2024, 5, 15)
    frame_early, _ = leave_missing_builder.build_features(early)
    frame_late, _ = leave_missing_builder.build_features(late)
    assert int(frame_early.notna().sum().sum()) <= int(frame_late.notna().sum().sum())


def test_build_features_respects_as_of_release_cutoff(
    feature_store: pd.DataFrame,
    series_meta: dict[str, dict[str, str]],
) -> None:
    """No feature may depend on a raw row released after as_of.

    Concrete check: as_of before employment's March print must not produce a
    non-null same-month employment MoM for Feb (employment Feb releases Mar 8).
    """
    builder = MonthlyFeatureBuilder(
        feature_store,
        recipe=FeatureRecipe(ragged_strategy="leave_missing"),
        series_meta=series_meta,
    )
    # Employment Feb 2024 releases 2024-03-08. Cutoff before that.
    frame, _ = builder.build_features(date(2024, 3, 7))
    col = "ca_lfs_employment__mom"
    assert col in frame.columns
    feb = pd.Period("2024-02", freq="M")
    if feb in frame.index:
        assert pd.isna(frame.loc[feb, col])


def test_features_hash_stable_for_same_inputs(
    leave_missing_builder: MonthlyFeatureBuilder,
) -> None:
    as_of = date(2024, 4, 1)
    _, meta_a = leave_missing_builder.build_features(as_of)
    _, meta_b = leave_missing_builder.build_features(as_of)
    assert meta_a.features_hash == meta_b.features_hash
    assert len(meta_a.features_hash) == 64
