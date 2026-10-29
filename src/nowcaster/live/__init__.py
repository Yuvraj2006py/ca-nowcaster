"""Scheduled refresh, predict, and scoring jobs (Role 6 — Live Pipeline).

Production model is AR(1) per Phase 3 Evaluation Skeptic verdict
(docs/evaluation_report.md): no candidate beats the baseline with DM + bootstrap
support. See nowcaster.live.production for the documented rationale.
"""

from nowcaster.live.dry_run import DryRunResult, assert_dry_run_ok, run_dry_run
from nowcaster.live.failures import IngestFailureError, PipelineFailure, record_ingest_failure
from nowcaster.live.predict_job import PredictResult, run_predict_job
from nowcaster.live.production import (
    PRODUCTION_MODEL_NAME,
    PRODUCTION_MODEL_RATIONALE,
    PRODUCTION_MODEL_VERSION,
    production_model_meta,
)
from nowcaster.live.score_job import ScoreJobResult, run_score_job

__all__ = [
    "DryRunResult",
    "IngestFailureError",
    "PipelineFailure",
    "PRODUCTION_MODEL_NAME",
    "PRODUCTION_MODEL_RATIONALE",
    "PRODUCTION_MODEL_VERSION",
    "PredictResult",
    "ScoreJobResult",
    "assert_dry_run_ok",
    "production_model_meta",
    "record_ingest_failure",
    "run_dry_run",
    "run_predict_job",
    "run_score_job",
]
