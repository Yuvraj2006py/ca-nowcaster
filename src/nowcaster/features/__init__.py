"""Leakage-safe monthly feature construction.

Public API for Role 3 (Feature Engineer). Consumes quality.as_of + the raw
store contract; does not import ingest internals.
"""

from nowcaster.features.builder import MonthlyFeatureBuilder, compute_features_hash
from nowcaster.features.ragged import RaggedEdgeStrategy, apply_ragged_edge
from nowcaster.features.recipe import DEFAULT_RECIPE, FeatureRecipe, FeatureSpec
from nowcaster.features.summary import (
    build_summary_rows,
    missing_rates,
    render_feature_summary_markdown,
    write_feature_summary,
)
from nowcaster.features.transforms import lag, log_diff, mom_growth, rolling_mean, yoy_growth

__all__ = [
    "DEFAULT_RECIPE",
    "FeatureRecipe",
    "FeatureSpec",
    "MonthlyFeatureBuilder",
    "RaggedEdgeStrategy",
    "apply_ragged_edge",
    "build_summary_rows",
    "compute_features_hash",
    "lag",
    "log_diff",
    "missing_rates",
    "mom_growth",
    "render_feature_summary_markdown",
    "rolling_mean",
    "write_feature_summary",
    "yoy_growth",
]
