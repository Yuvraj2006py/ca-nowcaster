"""Declarative feature recipe used for naming and features_hash."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class FeatureRecipe:
    """Immutable recipe for monthly feature construction.

    Inputs: transform/lag choices chosen by Feature Engineer (no data values).
    Outputs: hashable config embedded in features_hash.
    Time allowed to know: n/a (config only).
    """

    mom: bool = True
    yoy: bool = True
    log_diff: bool = True
    rolling_windows: tuple[int, ...] = (3,)
    mom_lags: tuple[int, ...] = (0, 1, 2, 3)
    # Primary target: only lagged MoM (never contemporaneous label as a feature).
    target_mom_lags: tuple[int, ...] = (1, 2, 3)
    ragged_strategy: str = "leave_missing"
    version: str = "v1"

    def to_dict(self) -> dict[str, object]:
        """Serialize for hashing / docs."""
        return asdict(self)


DEFAULT_RECIPE = FeatureRecipe()


@dataclass(frozen=True)
class FeatureSpec:
    """One column in the feature frame.

    Inputs: naming fields derived from recipe + series registry metadata.
    Outputs: documentation / summary row.
    Time allowed to know: n/a.
    """

    name: str
    source_series_id: str
    source: str  # statcan | boc_valet | derived
    transform: str
    lag: int
    notes: str = ""


def indicator_feature_specs(
    series_id: str,
    source: str,
    recipe: FeatureRecipe = DEFAULT_RECIPE,
) -> list[FeatureSpec]:
    """Expand recipe into FeatureSpec rows for an indicator series."""
    specs: list[FeatureSpec] = []
    if recipe.mom:
        for lag in recipe.mom_lags:
            specs.append(
                FeatureSpec(
                    name=_name(series_id, "mom", lag=lag),
                    source_series_id=series_id,
                    source=source,
                    transform="mom",
                    lag=lag,
                    notes="MoM % growth; lag months on growth series",
                )
            )
    if recipe.yoy:
        specs.append(
            FeatureSpec(
                name=_name(series_id, "yoy", lag=0),
                source_series_id=series_id,
                source=source,
                transform="yoy",
                lag=0,
                notes="YoY % growth (needs 12 months of levels)",
            )
        )
    if recipe.log_diff:
        specs.append(
            FeatureSpec(
                name=_name(series_id, "logdiff", lag=0),
                source_series_id=series_id,
                source=source,
                transform="logdiff",
                lag=0,
                notes="Δ log(level)",
            )
        )
    for window in recipe.rolling_windows:
        specs.append(
            FeatureSpec(
                name=_name(series_id, f"rollmean{window}", lag=0),
                source_series_id=series_id,
                source=source,
                transform=f"rollmean{window}",
                lag=0,
                notes=f"Trailing {window}-month mean of levels",
            )
        )
    return specs


def target_feature_specs(
    series_id: str,
    source: str,
    recipe: FeatureRecipe = DEFAULT_RECIPE,
) -> list[FeatureSpec]:
    """Lagged MoM features from the primary target level series (no lag 0)."""
    specs: list[FeatureSpec] = []
    for lag in recipe.target_mom_lags:
        if lag < 1:
            continue
        specs.append(
            FeatureSpec(
                name=_name(series_id, "mom", lag=lag),
                source_series_id=series_id,
                source=source,
                transform="mom",
                lag=lag,
                notes="Lagged target MoM only — contemporaneous target excluded",
            )
        )
    return specs


def _name(series_id: str, transform: str, *, lag: int) -> str:
    if lag == 0:
        return f"{series_id}__{transform}"
    return f"{series_id}__{transform}_lag{lag}"


@dataclass
class RecipeRegistry:
    """Optional map of series_id -> source for summary generation."""

    sources: dict[str, str] = field(default_factory=dict)
    roles: dict[str, str] = field(default_factory=dict)
