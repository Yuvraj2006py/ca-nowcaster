"""Scheduled predict job: refresh → features as-of now → AR(1) → append log."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nowcaster.contracts import PredictionLogEntry
from nowcaster.features import MonthlyFeatureBuilder
from nowcaster.ingest.refresh import refresh_all
from nowcaster.ingest.registry import load_registry
from nowcaster.live.failures import IngestFailureError, record_ingest_failure
from nowcaster.live.paths import (
    failure_log_path,
    prediction_log_path,
    raw_store_path,
)
from nowcaster.live.prediction_log import append_prediction, make_prediction_id
from nowcaster.live.production import (
    PRIMARY_TARGET_SERIES_ID,
    PRODUCTION_MODEL_NAME,
    PRODUCTION_MODEL_RATIONALE,
    PRODUCTION_MODEL_VERSION,
)
from nowcaster.live.store_io import load_raw_store_frame
from nowcaster.live.target import next_unpublished_month, target_mom_as_of
from nowcaster.models import create_baseline

logger = logging.getLogger(__name__)

RefreshFn = Callable[..., Any]
LoadStoreFn = Callable[[Path | str | None], pd.DataFrame]


@dataclass(frozen=True)
class PredictResult:
    """Outcome of a predict job attempt.

    Inputs: produced by run_predict_job.
    Outputs: status for CLI / Actions; optional PredictionLogEntry.
    Time allowed to know: as_of_date used for the run.
    """

    # predicted | skipped_ingest_failure | skipped_insufficient_history | skipped_duplicate
    status: str
    as_of_date: date
    entry: PredictionLogEntry | None = None
    message: str = ""


def series_meta_from_registry(registry_path: Path | str | None = None) -> dict[str, dict[str, str]]:
    """Build series_meta map for MonthlyFeatureBuilder from the registry.

    Inputs: optional registry path.
    Outputs: series_id → {source, target_role}.
    Time allowed to know: registry metadata only.
    """
    definitions = load_registry(registry_path)
    return {d.series_id: {"source": d.source, "target_role": d.target_role} for d in definitions}


def run_predict_job(
    *,
    as_of_date: date | datetime | None = None,
    store_path: Path | str | None = None,
    prediction_path: Path | str | None = None,
    failure_path: Path | str | None = None,
    registry_path: Path | str | None = None,
    refresh: bool = True,
    refresh_fn: RefreshFn | None = None,
    load_store_fn: LoadStoreFn | None = None,
    open_issue_on_ingest_failure: bool = True,
    allow_duplicate_month: bool = False,
    predicted_at: datetime | None = None,
    simulate_ingest_failure: bool | str | None = None,
) -> PredictResult:
    """Refresh data (unless dry), build features, fit AR(1), append prediction log.

    Inputs: as_of cutoff (default UTC today); store/log paths; refresh flags;
            optional injectables for tests; simulate_ingest_failure for dry-run.
    Outputs: PredictResult; on ingest failure logs + skips predict (no stale forecast).
    Time allowed to know: only values with release_timestamp <= as_of_date.
    """
    if isinstance(as_of_date, datetime):
        as_of_day = as_of_date.date()
    elif as_of_date is None:
        as_of_day = datetime.now(UTC).date()
    else:
        as_of_day = as_of_date

    clock = predicted_at or datetime.now(UTC)
    pred_path = prediction_log_path(prediction_path)
    fail_path = failure_log_path(failure_path)
    store = raw_store_path(store_path)

    logger.info(
        "predict_job start as_of=%s model=%s@%s rationale_ref=docs/evaluation_report.md",
        as_of_day.isoformat(),
        PRODUCTION_MODEL_NAME,
        PRODUCTION_MODEL_VERSION,
    )
    logger.info("production_model_rationale=%s", PRODUCTION_MODEL_RATIONALE)

    if simulate_ingest_failure:
        message = (
            simulate_ingest_failure
            if isinstance(simulate_ingest_failure, str)
            else "simulated ingest API failure"
        )
        record_ingest_failure(
            failure_log=fail_path,
            message=message,
            details={"simulated": True, "as_of_date": as_of_day.isoformat()},
            open_issue=open_issue_on_ingest_failure,
            now=clock,
        )
        return PredictResult(
            status="skipped_ingest_failure",
            as_of_date=as_of_day,
            message=message,
        )

    if refresh:
        try:
            do_refresh = refresh_fn or refresh_all
            summary = do_refresh(registry_path=registry_path, store_path=store)
            logger.info(
                "refresh ok inserted=%s skipped=%s rows=%s",
                getattr(summary, "total_inserted", "?"),
                getattr(summary, "total_skipped", "?"),
                getattr(summary, "total_rows_after", "?"),
            )
        except Exception as exc:  # noqa: BLE001 — any ingest failure must skip predict
            record_ingest_failure(
                failure_log=fail_path,
                message=str(exc),
                details={"as_of_date": as_of_day.isoformat(), "exc_type": type(exc).__name__},
                open_issue=open_issue_on_ingest_failure,
                now=clock,
            )
            raise IngestFailureError(str(exc)) from exc

    loader = load_store_fn or load_raw_store_frame
    frame = loader(store)
    if frame.empty:
        msg = "raw store empty after refresh; refusing to predict on missing data"
        record_ingest_failure(
            failure_log=fail_path,
            message=msg,
            details={"as_of_date": as_of_day.isoformat()},
            open_issue=open_issue_on_ingest_failure,
            now=clock,
        )
        return PredictResult(status="skipped_ingest_failure", as_of_date=as_of_day, message=msg)

    history = target_mom_as_of(frame, as_of_day, series_id=PRIMARY_TARGET_SERIES_ID)
    target_month = next_unpublished_month(history)
    if target_month is None or len(history.mom) < 2:
        msg = (
            f"insufficient target history for AR(1): n={len(history.mom)} "
            f"last_published={history.last_published_ref_month}"
        )
        logger.warning(msg)
        return PredictResult(
            status="skipped_insufficient_history",
            as_of_date=as_of_day,
            message=msg,
        )

    # Features as-of now (hash for audit); AR(1) ignores columns but contract requires hash.
    meta_map = series_meta_from_registry(registry_path)
    builder = MonthlyFeatureBuilder(frame, series_meta=meta_map)
    features, feat_meta = builder.build_features(as_of_day)

    y = history.mom.astype(float)
    # One-row scaffold for a single forward step (baselines ignore feature values).
    x_scaffold = pd.DataFrame(index=[pd.Period(target_month, freq="M")])
    if not features.empty:
        # Prefer a single empty-column row aligned to target month for n_rows=1.
        x_scaffold = pd.DataFrame(
            np.zeros((1, 0), dtype=np.float64),
            index=[pd.Period(target_month, freq="M")],
        )

    model = create_baseline(PRODUCTION_MODEL_NAME)
    model.fit(features if not features.empty else x_scaffold, y)
    prediction = model.predict(x_scaffold)

    point = float(prediction.points[0])
    interval = prediction.intervals[0]
    prev_mom = float(y.iloc[-1])
    direction_beat_prev = point > prev_mom

    entry = PredictionLogEntry(
        prediction_id=make_prediction_id(target_ref_month=target_month, predicted_at=clock),
        target_ref_month=target_month,
        predicted_at=clock,
        model_name=prediction.model_name,
        model_version=prediction.model_version,
        features_hash=feat_meta.features_hash,
        point=point,
        lower_80=interval.lower_80,
        upper_80=interval.upper_80,
        lower_95=interval.lower_95,
        upper_95=interval.upper_95,
        direction_beat_prev=direction_beat_prev,
        extras={
            "as_of_date": as_of_day.isoformat(),
            "production_rationale": "see docs/live_pipeline.md / evaluation_report.md",
            "last_published_ref_month": (
                history.last_published_ref_month.isoformat()
                if history.last_published_ref_month
                else None
            ),
        },
    )

    try:
        append_prediction(pred_path, entry, allow_duplicate_month=allow_duplicate_month)
    except ValueError as exc:
        logger.warning("duplicate prediction skipped: %s", exc)
        return PredictResult(
            status="skipped_duplicate",
            as_of_date=as_of_day,
            entry=entry,
            message=str(exc),
        )

    logger.info(
        "predicted id=%s month=%s point=%.6f model=%s@%s hash=%s",
        entry.prediction_id,
        entry.target_ref_month.isoformat(),
        entry.point,
        entry.model_name,
        entry.model_version,
        entry.features_hash[:12],
    )
    return PredictResult(status="predicted", as_of_date=as_of_day, entry=entry, message="ok")
