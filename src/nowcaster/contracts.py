"""Shared interfaces and schemas for ca-nowcaster.

Every agent must implement against these contracts. Do not invent parallel
schemas. Change requests go in docs/requests/, not silent edits here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# 1. Series registry (series_registry.yaml)
# ---------------------------------------------------------------------------
# See series_registry.yaml for the on-disk schema. In memory:


@dataclass(frozen=True)
class SeriesDefinition:
    """One verified series entry from the registry.

    Inputs: fields loaded from series_registry.yaml after metadata verification.
    Outputs: immutable description used by ingest and features.
    Time allowed to know: registry metadata only; no observation values.
    """

    series_id: str
    source: str  # "statcan" | "boc_valet"
    table_id: str | None
    vector_id: str | None
    valet_series: str | None
    name: str
    frequency: str  # e.g. "monthly"
    unit: str
    verified_at: datetime | None
    verification_notes: str
    target_role: str  # "primary_target" | "secondary_target" | "indicator"


# ---------------------------------------------------------------------------
# 2. Raw store schema (append-only vintages)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RawObservation:
    """One vintage of one observation in the raw store.

    Inputs: API payload plus retrieval clock.
    Outputs: append-only row; never update in place.
    Time allowed to know: release_timestamp as published; retrieved_at = fetch time.
    """

    series_id: str
    ref_period: date  # reference period the value describes
    value: float
    release_timestamp: datetime  # when the value became public
    retrieved_at: datetime  # when we fetched this vintage


RAW_STORE_COLUMNS: tuple[str, ...] = (
    "series_id",
    "ref_period",
    "value",
    "release_timestamp",
    "retrieved_at",
)


# ---------------------------------------------------------------------------
# 3. Feature frame
# ---------------------------------------------------------------------------
# Index = target reference month (Period[M] or first-of-month Timestamp).
# build_features(as_of_date) must not use any value with release_timestamp > as_of_date.


@dataclass(frozen=True)
class FeatureFrameMeta:
    """Metadata accompanying a feature matrix.

    Inputs: as_of_date used to build the frame; hash of feature recipe + inputs.
    Outputs: audit trail for leakage and reproducibility checks.
    Time allowed to know: as_of_date only for what enters the matrix.
    """

    as_of_date: date
    features_hash: str
    index_name: str = "ref_month"


@runtime_checkable
class FeatureBuilder(Protocol):
    def build_features(self, as_of_date: date) -> tuple[Any, FeatureFrameMeta]:
        """Build monthly feature frame available as of as_of_date.

        Inputs: as_of_date (inclusive public-knowledge cutoff).
        Outputs: (DataFrame indexed by target reference month, FeatureFrameMeta).
        Time allowed to know: only values with release_timestamp <= as_of_date.
        """
        ...


# ---------------------------------------------------------------------------
# 4. Model interface
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredictionIntervals:
    """Point prediction with 80% and 95% prediction intervals."""

    point: float
    lower_80: float
    upper_80: float
    lower_95: float
    upper_95: float


@dataclass(frozen=True)
class ModelPrediction:
    """Batch of predictions aligned to rows of X."""

    points: Any  # array-like
    intervals: list[PredictionIntervals]
    model_name: str
    model_version: str


@runtime_checkable
class NowcastModel(Protocol):
    name: str
    version: str

    def fit(self, X: Any, y: Any) -> NowcastModel:
        """Fit on feature matrix X and target y.

        Inputs: X (features), y (target MoM growth or class labels).
        Outputs: self (fitted).
        Time allowed to know: only rows whose features were built with a valid as_of.
        """
        ...

    def predict(self, X: Any) -> ModelPrediction:
        """Predict point estimates plus 80%/95% intervals.

        Inputs: X (features for periods to score).
        Outputs: ModelPrediction with point and intervals per row.
        Time allowed to know: same as fit; no future actuals.
        """
        ...


# ---------------------------------------------------------------------------
# 5. Prediction log schema (append-only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredictionLogEntry:
    """One logged nowcast before an official release.

    Inputs: model output at prediction time.
    Outputs: append-only public record for scoring later.
    Time allowed to know: everything public at predicted_at; not the eventual actual.
    """

    prediction_id: str
    target_ref_month: date
    predicted_at: datetime
    model_name: str
    model_version: str
    features_hash: str
    point: float
    lower_80: float
    upper_80: float
    lower_95: float
    upper_95: float
    direction_beat_prev: bool | None = None
    extras: dict[str, Any] = field(default_factory=dict)


PREDICTION_LOG_COLUMNS: tuple[str, ...] = (
    "prediction_id",
    "target_ref_month",
    "predicted_at",
    "model_name",
    "model_version",
    "features_hash",
    "point",
    "lower_80",
    "upper_80",
    "lower_95",
    "upper_95",
    "direction_beat_prev",
)


# ---------------------------------------------------------------------------
# 6. Score schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoreEntry:
    """Score of one prediction against the realized official value.

    Inputs: PredictionLogEntry plus actual after release.
    Outputs: append-only score row.
    Time allowed to know: actual only after its release_timestamp.
    """

    prediction_id: str
    scored_at: datetime
    actual: float
    error: float  # point - actual (signed)
    abs_error: float
    squared_error: float
    actual_in_80: bool
    actual_in_95: bool
    direction_correct: bool | None = None


SCORE_COLUMNS: tuple[str, ...] = (
    "prediction_id",
    "scored_at",
    "actual",
    "error",
    "abs_error",
    "squared_error",
    "actual_in_80",
    "actual_in_95",
    "direction_correct",
)
