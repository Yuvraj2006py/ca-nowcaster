"""Leakage-safe monthly feature builder (Role 3).

Pipeline: raw store → quality.as_of → monthly levels panel → ragged edge →
transforms / lags → FeatureFrameMeta with features_hash.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any

import pandas as pd

from nowcaster.contracts import FeatureFrameMeta
from nowcaster.features.ragged import RaggedEdgeStrategy, apply_ragged_edge
from nowcaster.features.recipe import (
    DEFAULT_RECIPE,
    FeatureRecipe,
    FeatureSpec,
    indicator_feature_specs,
    target_feature_specs,
)
from nowcaster.features.transforms import lag, log_diff, mom_growth, rolling_mean, yoy_growth
from nowcaster.quality.release_calendar import as_of

PRIMARY_TARGET_ROLE = "primary_target"
INDEX_NAME = "ref_month"


class MonthlyFeatureBuilder:
    """Build a monthly feature frame available as of a public-knowledge cutoff.

    Consumes the raw-store contract via ``quality.as_of`` only — does not import
    ingest internals.
    """

    def __init__(
        self,
        store: pd.DataFrame,
        *,
        recipe: FeatureRecipe | None = None,
        series_meta: dict[str, dict[str, str]] | None = None,
        indicator_ids: list[str] | None = None,
        primary_target_id: str | None = None,
    ) -> None:
        """Configure the builder.

        Inputs: raw store DataFrame (RAW_STORE_COLUMNS); optional recipe;
                optional series_meta mapping series_id -> {source, target_role};
                optional explicit indicator / primary target ids.
        Outputs: configured builder (no features yet).
        Time allowed to know: store may contain future vintages; build_features
                filters them via as_of.
        """
        self._store = store
        self.recipe = recipe or DEFAULT_RECIPE
        self._series_meta = series_meta or {}
        self._indicator_ids = indicator_ids
        self._primary_target_id = primary_target_id

    def build_features(self, as_of_date: date | datetime) -> tuple[pd.DataFrame, FeatureFrameMeta]:
        """Build monthly feature frame available as of as_of_date.

        Inputs: as_of_date (inclusive public-knowledge cutoff).
        Outputs: (DataFrame indexed by target reference month, FeatureFrameMeta).
        Time allowed to know: only values with release_timestamp <= as_of_date
                (enforced by quality.as_of before any transform).
        """
        if isinstance(as_of_date, datetime):
            as_of_day = as_of_date.date()
        else:
            as_of_day = as_of_date

        view = as_of(self._store, as_of_date)
        levels = _levels_panel(view)
        levels = _extend_index_through_as_of_month(levels, as_of_day)
        levels = apply_ragged_edge(
            levels,
            RaggedEdgeStrategy(self.recipe.ragged_strategy),
        )

        indicator_ids, target_id = self._resolve_series(levels.columns.tolist())
        frame = self._assemble_features(levels, indicator_ids=indicator_ids, target_id=target_id)
        frame.index.name = INDEX_NAME

        features_hash = compute_features_hash(
            recipe=self.recipe,
            as_of_date=as_of_day,
            as_of_view=view,
            feature_columns=list(frame.columns),
        )
        meta = FeatureFrameMeta(
            as_of_date=as_of_day,
            features_hash=features_hash,
            index_name=INDEX_NAME,
        )
        return frame, meta

    def feature_specs(self) -> list[FeatureSpec]:
        """Return FeatureSpec rows for the configured series set.

        Inputs: builder configuration / store series ids.
        Outputs: list of FeatureSpec (documentation / summary).
        Time allowed to know: registry-like metadata only; may peek store series
                ids (not values) when meta is incomplete.
        """
        # Prefer configured meta; fall back to ids seen in store.
        all_ids = sorted(
            set(self._series_meta) | set(self._store["series_id"].astype(str).unique().tolist())
        )
        indicator_ids, target_id = self._resolve_series(all_ids)
        specs: list[FeatureSpec] = []
        for sid in indicator_ids:
            source = self._series_meta.get(sid, {}).get("source", "unknown")
            specs.extend(indicator_feature_specs(sid, source, self.recipe))
        if target_id is not None:
            source = self._series_meta.get(target_id, {}).get("source", "unknown")
            specs.extend(target_feature_specs(target_id, source, self.recipe))
        return specs

    def _resolve_series(self, available_ids: list[str]) -> tuple[list[str], str | None]:
        if self._indicator_ids is not None or self._primary_target_id is not None:
            indicators = list(self._indicator_ids or [])
            return indicators, self._primary_target_id

        indicators: list[str] = []
        target_id: str | None = None
        for sid in available_ids:
            role = self._series_meta.get(sid, {}).get("target_role", "indicator")
            if role == PRIMARY_TARGET_ROLE:
                target_id = sid
            else:
                indicators.append(sid)
        # If meta missing, treat every series as indicator except well-known GDP id.
        if not self._series_meta:
            if "ca_gdp_basic_prices" in available_ids:
                target_id = "ca_gdp_basic_prices"
                indicators = [s for s in available_ids if s != target_id]
            else:
                indicators = list(available_ids)
                target_id = None
        return sorted(indicators), target_id

    def _assemble_features(
        self,
        levels: pd.DataFrame,
        *,
        indicator_ids: list[str],
        target_id: str | None,
    ) -> pd.DataFrame:
        columns: dict[str, pd.Series] = {}
        for sid in indicator_ids:
            if sid not in levels.columns:
                continue
            level = levels[sid]
            mom = mom_growth(level)
            if self.recipe.mom:
                for lag_n in self.recipe.mom_lags:
                    columns[_col(sid, "mom", lag_n)] = lag(mom, lag_n)
            if self.recipe.yoy:
                columns[_col(sid, "yoy", 0)] = yoy_growth(level)
            if self.recipe.log_diff:
                columns[_col(sid, "logdiff", 0)] = log_diff(level)
            for window in self.recipe.rolling_windows:
                columns[_col(sid, f"rollmean{window}", 0)] = rolling_mean(level, window)

        if target_id is not None and target_id in levels.columns:
            target_mom = mom_growth(levels[target_id])
            for lag_n in self.recipe.target_mom_lags:
                if lag_n < 1:
                    continue
                columns[_col(target_id, "mom", lag_n)] = lag(target_mom, lag_n)

        if not columns:
            return pd.DataFrame(index=levels.index)

        frame = pd.DataFrame(columns, index=levels.index)
        # Stable column order for hashing / reproducibility.
        return frame.reindex(columns=sorted(frame.columns))


def _col(series_id: str, transform: str, lag_n: int) -> str:
    if lag_n == 0:
        return f"{series_id}__{transform}"
    return f"{series_id}__{transform}_lag{lag_n}"


def _levels_panel(as_of_view: pd.DataFrame) -> pd.DataFrame:
    """Pivot as_of view to wide monthly levels (Period[M] index).

    Inputs: as_of-filtered RAW_STORE_COLUMNS frame.
    Outputs: columns=series_id, index=monthly Period, values=level.
    Time allowed to know: only rows already in the as_of view.
    """
    if as_of_view.empty:
        return pd.DataFrame()

    frame = as_of_view.copy()
    frame["ref_month"] = pd.PeriodIndex(
        pd.to_datetime(frame["ref_period"]),
        freq="M",
    )
    # One value per (series, month) — as_of already latest vintage.
    pivoted = frame.pivot_table(
        index="ref_month",
        columns="series_id",
        values="value",
        aggfunc="last",
    )
    pivoted = pivoted.sort_index()
    # Ensure continuous monthly index between first and last observed month.
    if len(pivoted.index) == 0:
        return pivoted
    full_index = pd.period_range(pivoted.index.min(), pivoted.index.max(), freq="M")
    return pivoted.reindex(full_index)


def _extend_index_through_as_of_month(levels: pd.DataFrame, as_of_day: date) -> pd.DataFrame:
    """Extend the panel index through the as_of calendar month (ragged edge).

    Inputs: monthly levels panel; as_of calendar date.
    Outputs: panel reindexed through Period(as_of month); new months are NaN
             until ragged fill runs.
    Time allowed to know: as_of month boundary only; no new observation values.
    """
    as_of_period = pd.Period(as_of_day, freq="M")
    if levels.empty:
        return pd.DataFrame(index=pd.PeriodIndex([as_of_period], freq="M"))
    start = levels.index.min()
    end = max(levels.index.max(), as_of_period)
    full_index = pd.period_range(start, end, freq="M")
    return levels.reindex(full_index)


def compute_features_hash(
    *,
    recipe: FeatureRecipe,
    as_of_date: date,
    as_of_view: pd.DataFrame,
    feature_columns: list[str],
) -> str:
    """Stable SHA-256 over recipe + as_of inputs + column names.

    Inputs: recipe; as_of_date; as_of view used as the sole data input;
            ordered feature column names.
    Outputs: hex digest string.
    Time allowed to know: contents of as_of_view only (already filtered).
    """
    payload: dict[str, Any] = {
        "recipe": recipe.to_dict(),
        "as_of_date": as_of_date.isoformat(),
        "feature_columns": list(feature_columns),
        "inputs": _view_fingerprint(as_of_view),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _view_fingerprint(view: pd.DataFrame) -> list[list[object]]:
    if view.empty:
        return []
    cols = ["series_id", "ref_period", "value", "release_timestamp"]
    subset = view.loc[:, cols].copy()
    subset["ref_period"] = subset["ref_period"].map(
        lambda d: d.isoformat() if hasattr(d, "isoformat") else str(d)
    )
    subset["release_timestamp"] = pd.to_datetime(subset["release_timestamp"]).astype(str)
    subset["value"] = subset["value"].astype(float)
    subset = subset.sort_values(cols).reset_index(drop=True)
    return subset.values.tolist()
