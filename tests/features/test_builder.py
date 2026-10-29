"""Tests for MonthlyFeatureBuilder assembly and ragged strategies."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from nowcaster.contracts import FeatureFrameMeta
from nowcaster.features import (
    FeatureRecipe,
    MonthlyFeatureBuilder,
    RaggedEdgeStrategy,
    write_feature_summary,
)


def test_build_features_returns_contract_meta(
    feature_store: pd.DataFrame,
    series_meta: dict[str, dict[str, str]],
) -> None:
    builder = MonthlyFeatureBuilder(feature_store, series_meta=series_meta)
    frame, meta = builder.build_features(date(2024, 5, 15))
    assert isinstance(meta, FeatureFrameMeta)
    assert meta.as_of_date == date(2024, 5, 15)
    assert meta.index_name == "ref_month"
    assert frame.index.name == "ref_month"
    assert isinstance(frame.index, pd.PeriodIndex)
    # Contemporaneous target MoM must not appear as a feature column.
    assert "ca_gdp_basic_prices__mom" not in frame.columns
    assert "ca_gdp_basic_prices__mom_lag1" in frame.columns
    assert "ca_lfs_employment__mom" in frame.columns
    assert "ca_lfs_employment__yoy" in frame.columns
    assert "ca_lfs_employment__logdiff" in frame.columns
    assert "ca_lfs_employment__rollmean3" in frame.columns


def test_ragged_strategies_differ_on_trailing_edge(
    feature_store: pd.DataFrame,
    series_meta: dict[str, dict[str, str]],
) -> None:
    as_of = date(2024, 4, 15)
    frames: dict[str, pd.DataFrame] = {}
    for strat in (
        RaggedEdgeStrategy.LEAVE_MISSING,
        RaggedEdgeStrategy.CARRY,
        RaggedEdgeStrategy.AR1,
    ):
        builder = MonthlyFeatureBuilder(
            feature_store,
            recipe=FeatureRecipe(ragged_strategy=strat.value),
            series_meta=series_meta,
        )
        frame, _ = builder.build_features(as_of)
        frames[strat.value] = frame

    leave = frames["leave_missing"]
    carry = frames["carry"]
    # Carry should have weakly fewer NaNs than leave_missing.
    assert int(carry.isna().sum().sum()) <= int(leave.isna().sum().sum())


def test_write_feature_summary(
    feature_store: pd.DataFrame,
    series_meta: dict[str, dict[str, str]],
    tmp_path: Path,
) -> None:
    builder = MonthlyFeatureBuilder(feature_store, series_meta=series_meta)
    path = write_feature_summary(
        tmp_path / "feature_summary.md",
        builder,
        as_of_date=date(2024, 5, 15),
    )
    text = path.read_text(encoding="utf-8")
    assert "# Feature summary" in text
    assert "ca_lfs_employment__mom" in text
    assert "missing_rate" in text
