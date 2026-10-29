"""Append-only score log matching contracts.ScoreEntry / SCORE_COLUMNS."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

from nowcaster.contracts import SCORE_COLUMNS, PredictionLogEntry, ScoreEntry


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame({c: pd.Series(dtype="object") for c in SCORE_COLUMNS})


def load_score_log(path: Path | str) -> pd.DataFrame:
    """Load score log CSV (empty frame if missing).

    Inputs: path to scores.csv.
    Outputs: DataFrame with SCORE_COLUMNS.
    Time allowed to know: whatever was previously scored.
    """
    file_path = Path(path)
    if not file_path.exists() or file_path.stat().st_size == 0:
        return _empty_frame()
    frame = pd.read_csv(file_path)
    for col in SCORE_COLUMNS:
        if col not in frame.columns:
            frame[col] = None
    return frame.loc[:, list(SCORE_COLUMNS)]


def score_prediction(
    prediction: PredictionLogEntry,
    actual: float,
    *,
    scored_at: datetime,
    previous_actual: float | None = None,
) -> ScoreEntry:
    """Score one logged prediction against a realized official value.

    Inputs: PredictionLogEntry; actual MoM after release; scoring clock;
            optional previous month's actual for direction_correct.
    Outputs: ScoreEntry (error = point - actual).
    Time allowed to know: actual only after its release_timestamp (caller enforces).
    """
    error = float(prediction.point) - float(actual)
    abs_error = abs(error)
    squared_error = error * error
    actual_in_80 = prediction.lower_80 <= actual <= prediction.upper_80
    actual_in_95 = prediction.lower_95 <= actual <= prediction.upper_95

    direction_correct: bool | None = None
    if prediction.direction_beat_prev is not None and previous_actual is not None:
        actual_beat = float(actual) > float(previous_actual)
        direction_correct = bool(prediction.direction_beat_prev) == actual_beat

    return ScoreEntry(
        prediction_id=prediction.prediction_id,
        scored_at=scored_at,
        actual=float(actual),
        error=error,
        abs_error=abs_error,
        squared_error=squared_error,
        actual_in_80=actual_in_80,
        actual_in_95=actual_in_95,
        direction_correct=direction_correct,
    )


def entry_to_row(entry: ScoreEntry) -> dict[str, object]:
    """Serialize a ScoreEntry to a CSV row dict.

    Inputs: ScoreEntry.
    Outputs: column→value mapping for SCORE_COLUMNS.
    Time allowed to know: fields already on the entry.
    """
    return {
        "prediction_id": entry.prediction_id,
        "scored_at": entry.scored_at.isoformat(),
        "actual": float(entry.actual),
        "error": float(entry.error),
        "abs_error": float(entry.abs_error),
        "squared_error": float(entry.squared_error),
        "actual_in_80": entry.actual_in_80,
        "actual_in_95": entry.actual_in_95,
        "direction_correct": entry.direction_correct,
    }


def append_score(path: Path | str, entry: ScoreEntry) -> ScoreEntry:
    """Append one score row (creates file + header if needed).

    Inputs: log path; ScoreEntry.
    Outputs: the appended entry.
    Time allowed to know: entry fields only.
    Raises: ValueError if prediction_id already scored (append-only).
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_score_log(file_path)
    if not existing.empty:
        ids = existing["prediction_id"].astype(str)
        if (ids == entry.prediction_id).any():
            raise ValueError(
                f"prediction_id={entry.prediction_id!r} already scored; "
                "refusing to overwrite (append-only)"
            )

    row = entry_to_row(entry)
    new_frame = pd.DataFrame([row], columns=list(SCORE_COLUMNS))
    write_header = not file_path.exists() or file_path.stat().st_size == 0
    new_frame.to_csv(file_path, mode="a", header=write_header, index=False)
    return entry


def prediction_from_row(row: dict[str, object]) -> PredictionLogEntry:
    """Rebuild a PredictionLogEntry from a CSV row dict.

    Inputs: prediction log row.
    Outputs: PredictionLogEntry.
    Time allowed to know: row fields only.
    """
    target = row["target_ref_month"]
    if isinstance(target, str):
        target_date = date_from_iso(target)
    else:
        target_date = target  # type: ignore[assignment]

    predicted_at = row["predicted_at"]
    if isinstance(predicted_at, str):
        predicted_dt = datetime.fromisoformat(predicted_at)
    else:
        predicted_dt = predicted_at  # type: ignore[assignment]

    direction = row.get("direction_beat_prev")
    if direction is None or (isinstance(direction, float) and pd.isna(direction)):
        direction_bool: bool | None = None
    else:
        direction_bool = (
            bool(direction)
            if not isinstance(direction, str)
            else direction.lower()
            in {
                "true",
                "1",
                "yes",
            }
        )

    return PredictionLogEntry(
        prediction_id=str(row["prediction_id"]),
        target_ref_month=target_date,
        predicted_at=predicted_dt,
        model_name=str(row["model_name"]),
        model_version=str(row["model_version"]),
        features_hash=str(row["features_hash"]),
        point=float(row["point"]),
        lower_80=float(row["lower_80"]),
        upper_80=float(row["upper_80"]),
        lower_95=float(row["lower_95"]),
        upper_95=float(row["upper_95"]),
        direction_beat_prev=direction_bool,
    )


def date_from_iso(value: str) -> date:
    """Parse YYYY-MM-DD (or YYYY-MM) into a date.

    Inputs: ISO date string.
    Outputs: datetime.date.
    Time allowed to know: none.
    """
    text = str(value).strip()
    if len(text) == 7 and text[4] == "-":
        text = f"{text}-01"
    return date.fromisoformat(text[:10])
