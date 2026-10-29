"""Production model selection documents the Phase 3 honest-result choice."""

from __future__ import annotations

from pathlib import Path

from nowcaster.live.production import (
    PRODUCTION_MODEL_NAME,
    PRODUCTION_MODEL_RATIONALE,
    PRODUCTION_MODEL_VERSION,
    production_model_meta,
)
from nowcaster.models import create_baseline


def test_production_model_is_ar1_matching_registry() -> None:
    assert PRODUCTION_MODEL_NAME == "ar1"
    assert PRODUCTION_MODEL_VERSION == "0.1.0"
    model = create_baseline(PRODUCTION_MODEL_NAME)
    assert model.name == PRODUCTION_MODEL_NAME
    assert model.version == PRODUCTION_MODEL_VERSION
    meta = production_model_meta()
    assert "evaluation_report" in meta["rationale"] or "Phase 3" in meta["rationale"]
    assert (
        "honest" in PRODUCTION_MODEL_RATIONALE.lower()
        or "beat" in PRODUCTION_MODEL_RATIONALE.lower()
    )


def test_live_pipeline_doc_exists() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "docs" / "live_pipeline.md").read_text(encoding="utf-8")
    assert "AR(1)" in text or "ar1" in text
    assert "evaluation_report" in text
    assert (root / ".github" / "workflows" / "live-predict.yml").exists()
    assert (root / ".github" / "workflows" / "live-score.yml").exists()
    assert (root / "docs" / "requests" / "devops-live-pipeline-workflows.md").exists()
