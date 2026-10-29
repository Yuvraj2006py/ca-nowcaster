"""Scoring job: when official GDP MoM appears, fill the score schema."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from nowcaster.contracts import ScoreEntry
from nowcaster.live.paths import prediction_log_path, raw_store_path, score_log_path
from nowcaster.live.prediction_log import list_unscored_predictions, load_prediction_log
from nowcaster.live.production import PRIMARY_TARGET_SERIES_ID
from nowcaster.live.score_log import (
    append_score,
    date_from_iso,
    load_score_log,
    prediction_from_row,
    score_prediction,
)
from nowcaster.live.store_io import load_raw_store_frame
from nowcaster.live.target import actual_mom_for_month

logger = logging.getLogger(__name__)

LoadStoreFn = Callable[[Path | str | None], pd.DataFrame]


@dataclass(frozen=True)
class ScoreJobResult:
    """Outcome of a scoring pass.

    Inputs: produced by run_score_job.
    Outputs: counts + new ScoreEntry list for CLI / Actions.
    Time allowed to know: as_of_date used for actuals lookup.
    """

    as_of_date: date
    scored: list[ScoreEntry]
    pending_without_actual: int
    message: str = ""


def run_score_job(
    *,
    as_of_date: date | datetime | None = None,
    store_path: Path | str | None = None,
    prediction_path: Path | str | None = None,
    score_path: Path | str | None = None,
    load_store_fn: LoadStoreFn | None = None,
    scored_at: datetime | None = None,
) -> ScoreJobResult:
    """Score unscored predictions whose official actual is public by as_of_date.

    Inputs: as_of cutoff (default UTC today); store + log paths; optional injectables.
    Outputs: ScoreJobResult with newly appended scores.
    Time allowed to know: only actuals with release_timestamp <= as_of_date.
    """
    if isinstance(as_of_date, datetime):
        as_of_day = as_of_date.date()
    elif as_of_date is None:
        as_of_day = datetime.now(UTC).date()
    else:
        as_of_day = as_of_date

    clock = scored_at or datetime.now(UTC)
    pred_path = prediction_log_path(prediction_path)
    sc_path = score_log_path(score_path)
    store = raw_store_path(store_path)

    predictions = load_prediction_log(pred_path)
    scores = load_score_log(sc_path)
    pending = list_unscored_predictions(predictions, scores)

    loader = load_store_fn or load_raw_store_frame
    frame = loader(store)

    newly_scored: list[ScoreEntry] = []
    still_pending = 0

    for row in pending:
        target_raw = row["target_ref_month"]
        target_month = (
            date_from_iso(str(target_raw)) if not isinstance(target_raw, date) else target_raw
        )
        assert isinstance(target_month, date)

        actual = actual_mom_for_month(
            frame,
            target_month,
            as_of_date=as_of_day,
            series_id=PRIMARY_TARGET_SERIES_ID,
        )
        if actual is None:
            still_pending += 1
            logger.info(
                "actual not yet public for %s as_of %s; leaving unscored",
                target_month.isoformat(),
                as_of_day.isoformat(),
            )
            continue

        # Previous month's actual for direction_correct (also as_of-filtered).
        prev_period = pd.Period(target_month, freq="M") - 1
        prev_month = date(prev_period.year, prev_period.month, 1)
        previous_actual = actual_mom_for_month(
            frame,
            prev_month,
            as_of_date=as_of_day,
            series_id=PRIMARY_TARGET_SERIES_ID,
        )

        prediction = prediction_from_row(row)
        entry = score_prediction(
            prediction,
            actual,
            scored_at=clock,
            previous_actual=previous_actual,
        )
        append_score(sc_path, entry)
        newly_scored.append(entry)
        logger.info(
            "scored id=%s actual=%.6f abs_error=%.6f in80=%s in95=%s",
            entry.prediction_id,
            entry.actual,
            entry.abs_error,
            entry.actual_in_80,
            entry.actual_in_95,
        )

    return ScoreJobResult(
        as_of_date=as_of_day,
        scored=newly_scored,
        pending_without_actual=still_pending,
        message=f"scored={len(newly_scored)} pending={still_pending}",
    )
