"""Append-only prediction log matching contracts.PredictionLogEntry / PREDICTION_LOG_COLUMNS."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from nowcaster.contracts import PREDICTION_LOG_COLUMNS, PredictionLogEntry


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in PREDICTION_LOG_COLUMNS})


def load_prediction_log(path: Path | str) -> pd.DataFrame:
    """Load prediction log CSV (empty frame if missing).

    Inputs: path to predictions.csv.
    Outputs: DataFrame with PREDICTION_LOG_COLUMNS.
    Time allowed to know: whatever was previously logged.
    """
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        return _empty_frame()
    frame = pd.read_csv(file_path)
    for col in PREDICTION_LOG_COLUMNS:
        if col not in frame.columns:
            frame[col] = None
    return frame.loc[:, list(PREDICTION_LOG_COLUMNS)]


def entry_to_row(entry: PredictionLogEntry) -> dict[str, object]:
    """Serialize a PredictionLogEntry to a CSV row dict.

    Inputs: PredictionLogEntry.
    Outputs: column→value mapping for PREDICTION_LOG_COLUMNS.
    Time allowed to know: fields already on the entry.
    """
    return {
        "prediction_id": entry.prediction_id,
        "target_ref_month": entry.target_ref_month.isoformat(),
        "predicted_at": entry.predicted_at.isoformat(),
        "model_name": entry.model_name,
        "model_version": entry.model_version,
        "features_hash": entry.features_hash,
        "point": float(entry.point),
        "lower_80": float(entry.lower_80),
        "upper_80": float(entry.upper_80),
        "lower_95": float(entry.lower_95),
        "upper_95": float(entry.upper_95),
        "direction_beat_prev": entry.direction_beat_prev,
    }


def append_prediction(
    path: Path | str,
    entry: PredictionLogEntry,
    *,
    allow_duplicate_month: bool = False,
) -> PredictionLogEntry:
    """Append one prediction to the log (creates file + header if needed).

    Inputs: log path; PredictionLogEntry; duplicate-month policy.
    Outputs: the appended entry (unchanged).
    Time allowed to know: entry fields only; does not look at future actuals.
    Raises: ValueError if the same (target_ref_month, model_name, model_version)
            is already logged and allow_duplicate_month is False (idempotent
            double-run policy per docs/failure_modes.md).
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_prediction_log(file_path)
    month_key = entry.target_ref_month.isoformat()
    if not allow_duplicate_month and not existing.empty:
        dup = (
            (existing["target_ref_month"].astype(str) == month_key)
            & (existing["model_name"].astype(str) == entry.model_name)
            & (existing["model_version"].astype(str) == entry.model_version)
        )
        if bool(dup.any()):
            raise ValueError(
                f"prediction already logged for "
                f"(target_ref_month={month_key}, model={entry.model_name}"
                f"@{entry.model_version}); refusing to overwrite (append-only)"
            )

    row = entry_to_row(entry)
    new_frame = pd.DataFrame([row], columns=list(PREDICTION_LOG_COLUMNS))
    write_header = not file_path.exists() or file_path.stat().st_size == 0
    new_frame.to_csv(file_path, mode="a", header=write_header, index=False)
    return entry


def make_prediction_id(*, target_ref_month: date, predicted_at: datetime) -> str:
    """Build a stable-ish unique prediction id.

    Inputs: target month; prediction clock.
    Outputs: string id (uuid4 suffix for uniqueness).
    Time allowed to know: predicted_at clock only.
    """
    stamp = predicted_at.strftime("%Y%m%dT%H%M%SZ")
    month = target_ref_month.strftime("%Y-%m")
    return f"pred-{month}-{stamp}-{uuid.uuid4().hex[:8]}"


def list_unscored_predictions(
    prediction_log: pd.DataFrame,
    score_log: pd.DataFrame,
) -> list[dict[str, object]]:
    """Return prediction rows whose prediction_id is not yet in the score log.

    Inputs: prediction and score DataFrames.
    Outputs: list of prediction row dicts awaiting scores.
    Time allowed to know: log contents only.
    """
    if prediction_log.empty:
        return []
    scored_ids: set[str] = set()
    if not score_log.empty and "prediction_id" in score_log.columns:
        scored_ids = set(score_log["prediction_id"].astype(str))
    pending: list[dict[str, object]] = []
    for _, row in prediction_log.iterrows():
        pid = str(row["prediction_id"])
        if pid not in scored_ids:
            pending.append(row.to_dict())
    return pending
