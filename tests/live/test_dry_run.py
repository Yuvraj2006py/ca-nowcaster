"""Done criteria: dry-run logs prediction + scored replay; failed-API is graceful."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from nowcaster.live.dry_run import assert_dry_run_ok, run_dry_run
from nowcaster.live.prediction_log import load_prediction_log
from nowcaster.live.production import PRODUCTION_MODEL_NAME, PRODUCTION_MODEL_VERSION
from nowcaster.live.score_log import load_score_log


def test_dry_run_predict_score_and_failed_api(live_store: pd.DataFrame, tmp_path: Path) -> None:
    """Historical replay before Dec-2022 GDP release; score after it lands."""
    result = run_dry_run(
        store_frame=live_store,
        predict_as_of=date(2023, 2, 15),
        score_as_of=date(2023, 2, 28),
        work_dir=tmp_path / "dry",
        predicted_at=datetime(2023, 2, 15, 14, 0, 0, tzinfo=UTC),
        scored_at=datetime(2023, 2, 28, 16, 0, 0, tzinfo=UTC),
        simulate_failed_api=True,
        registry_path=None,
    )
    assert_dry_run_ok(result)

    assert result.predict is not None
    assert result.predict.entry is not None
    entry = result.predict.entry
    assert entry.model_name == PRODUCTION_MODEL_NAME
    assert entry.model_version == PRODUCTION_MODEL_VERSION
    assert entry.target_ref_month == date(2022, 12, 1)
    assert entry.features_hash  # non-empty audit hash

    preds = load_prediction_log(result.prediction_log)
    assert len(preds) == 1
    scores = load_score_log(result.score_log)
    assert len(scores) == 1
    assert scores.iloc[0]["prediction_id"] == entry.prediction_id

    assert result.failed_api is not None
    assert result.failed_api.status == "skipped_ingest_failure"
    fail_text = result.failure_log.read_text(encoding="utf-8")
    assert "simulated" in fail_text.lower() or "outage" in fail_text.lower()


def test_predict_job_skips_on_refresh_exception(live_store: pd.DataFrame, tmp_path: Path) -> None:
    from nowcaster.live.failures import IngestFailureError
    from nowcaster.live.predict_job import run_predict_job

    def boom(**_kwargs: object) -> None:
        raise RuntimeError("upstream 503")

    try:
        run_predict_job(
            as_of_date=date(2023, 2, 15),
            store_path=tmp_path / "unused.duckdb",
            prediction_path=tmp_path / "predictions.csv",
            failure_path=tmp_path / "failures.jsonl",
            refresh=True,
            refresh_fn=boom,
            load_store_fn=lambda _p=None: live_store,
            open_issue_on_ingest_failure=False,
            predicted_at=datetime(2023, 2, 15, 14, 0, 0, tzinfo=UTC),
        )
        raised = False
    except IngestFailureError:
        raised = True
    assert raised
    assert (tmp_path / "failures.jsonl").exists()
    # Must not have written a prediction on failure.
    assert not (tmp_path / "predictions.csv").exists()
