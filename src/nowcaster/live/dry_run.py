"""Dry-run path: historical replay (predict + score) and failed-API simulation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from nowcaster.contracts import PredictionLogEntry, ScoreEntry
from nowcaster.live.predict_job import PredictResult, run_predict_job
from nowcaster.live.score_job import ScoreJobResult, run_score_job

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DryRunResult:
    """Combined dry-run outcome for tests and CLI.

    Inputs: produced by run_dry_run.
    Outputs: predict + score results and optional failure simulation status.
    Time allowed to know: as_of dates supplied by the caller (historical).
    """

    predict: PredictResult | None
    score: ScoreJobResult | None
    failed_api: PredictResult | None
    prediction_log: Path
    score_log: Path
    failure_log: Path


def run_dry_run(
    *,
    store_frame: pd.DataFrame,
    predict_as_of: date,
    score_as_of: date,
    work_dir: Path | str,
    predicted_at: datetime | None = None,
    scored_at: datetime | None = None,
    simulate_failed_api: bool = True,
    registry_path: Path | str | None = None,
) -> DryRunResult:
    """Historical replay: log a prediction as_of predict_as_of, score as_of score_as_of.

    Also optionally simulates a failed ingest API and asserts predict is skipped.

    Inputs: in-memory raw store frame; predict/score cutoffs; work_dir for logs;
            clocks; whether to run failed-API simulation.
    Outputs: DryRunResult with logged prediction + scores + failure sim status.
    Time allowed to know: predict uses only releases <= predict_as_of;
            score uses only releases <= score_as_of.
    """
    root = Path(work_dir)
    root.mkdir(parents=True, exist_ok=True)
    pred_path = root / "predictions.csv"
    score_path = root / "scores.csv"
    fail_path = root / "failures.jsonl"
    # Dummy store path — load overridden via load_store_fn.
    store_path = root / "unused.duckdb"

    def _load(_path: Path | str | None = None) -> pd.DataFrame:
        return store_frame.copy()

    predict = run_predict_job(
        as_of_date=predict_as_of,
        store_path=store_path,
        prediction_path=pred_path,
        failure_path=fail_path,
        registry_path=registry_path,
        refresh=False,
        load_store_fn=_load,
        open_issue_on_ingest_failure=False,
        allow_duplicate_month=True,
        predicted_at=predicted_at,
    )
    logger.info("dry_run predict status=%s", predict.status)

    score: ScoreJobResult | None = None
    if predict.status == "predicted" and predict.entry is not None:
        score = run_score_job(
            as_of_date=score_as_of,
            store_path=store_path,
            prediction_path=pred_path,
            score_path=score_path,
            load_store_fn=_load,
            scored_at=scored_at,
        )
        logger.info("dry_run score %s", score.message)

    failed_api: PredictResult | None = None
    if simulate_failed_api:
        failed_api = run_predict_job(
            as_of_date=predict_as_of,
            store_path=store_path,
            prediction_path=root / "predictions_after_fail.csv",
            failure_path=fail_path,
            refresh=True,
            simulate_ingest_failure="dry-run simulated StatCan/Valet outage",
            open_issue_on_ingest_failure=False,
            predicted_at=predicted_at,
        )
        logger.info("dry_run failed_api status=%s", failed_api.status)

    return DryRunResult(
        predict=predict,
        score=score,
        failed_api=failed_api,
        prediction_log=pred_path,
        score_log=score_path,
        failure_log=fail_path,
    )


def assert_dry_run_ok(result: DryRunResult) -> None:
    """Raise AssertionError if dry-run did not log a prediction and score gracefully.

    Inputs: DryRunResult from run_dry_run.
    Outputs: None on success.
    Time allowed to know: result fields only.
    """
    if result.predict is None or result.predict.status != "predicted":
        raise AssertionError(f"expected predicted status, got {result.predict}")
    if result.predict.entry is None:
        raise AssertionError("expected PredictionLogEntry")
    if not isinstance(result.predict.entry, PredictionLogEntry):
        raise AssertionError("entry type mismatch")
    if result.score is None or len(result.score.scored) < 1:
        raise AssertionError(f"expected at least one score, got {result.score}")
    if not isinstance(result.score.scored[0], ScoreEntry):
        raise AssertionError("score entry type mismatch")
    if result.failed_api is None or result.failed_api.status != "skipped_ingest_failure":
        raise AssertionError(f"expected skipped_ingest_failure, got {result.failed_api}")
    if not result.failure_log.exists():
        raise AssertionError("failure log missing after simulated API failure")
