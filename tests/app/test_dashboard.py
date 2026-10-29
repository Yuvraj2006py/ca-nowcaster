"""Tests for the Streamlit dashboard log loaders and scoreboard (no live APIs)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from nowcaster.app.charts import history_frame, predictions_vs_actuals_chart
from nowcaster.app.copy_text import HOW_IT_WORKS, LIMITS
from nowcaster.app.load_logs import fixture_dir, live_logs_available, load_dashboard_bundle
from nowcaster.app.scoreboard import build_scoreboard, latest_headline
from nowcaster.contracts import PREDICTION_LOG_COLUMNS, SCORE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]


def test_fixtures_exist_and_match_contracts() -> None:
    fix = fixture_dir()
    pred = pd.read_csv(fix / "predictions.csv")
    score = pd.read_csv(fix / "scores.csv")
    for col in PREDICTION_LOG_COLUMNS:
        assert col in pred.columns, col
    for col in SCORE_COLUMNS:
        assert col in score.columns, col
    assert len(pred) > 0
    assert len(score) > 0


def test_load_bundle_falls_back_to_fixtures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NOWCASTER_PREDICTION_LOG", str(tmp_path / "missing_preds.csv"))
    monkeypatch.setenv("NOWCASTER_SCORE_LOG", str(tmp_path / "missing_scores.csv"))
    assert live_logs_available() is False
    bundle = load_dashboard_bundle()
    assert bundle.source == "fixture"
    assert not bundle.predictions.empty
    assert bundle.production_model == "ar1"
    assert "honest_verdict" in bundle.meta
    verdict = bundle.meta["honest_verdict"].lower()
    assert "ar(1)" in verdict or "ar1" in verdict


def test_load_bundle_uses_live_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src_pred = fixture_dir() / "predictions.csv"
    src_score = fixture_dir() / "scores.csv"
    live_pred = tmp_path / "predictions.csv"
    live_score = tmp_path / "scores.csv"
    live_pred.write_text(src_pred.read_text(encoding="utf-8"), encoding="utf-8")
    live_score.write_text(src_score.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("NOWCASTER_PREDICTION_LOG", str(live_pred))
    monkeypatch.setenv("NOWCASTER_SCORE_LOG", str(live_score))
    bundle = load_dashboard_bundle()
    assert bundle.source == "live"
    assert bundle.meta.get("using_sample_logs") is False


def test_headline_and_scoreboard_from_fixtures() -> None:
    bundle = load_dashboard_bundle(prefer_fixture=True)
    headline = latest_headline(
        bundle.predictions,
        bundle.scores,
        production_model=bundle.production_model,
        baseline_model=bundle.baseline_model,
    )
    assert headline is not None
    assert headline.production_model == "ar1"
    assert headline.baseline_point is not None
    assert headline.scored is False  # latest fixture month unscored

    cards = build_scoreboard(
        bundle.joined,
        production_model="ar1",
        baseline_model="last_value",
        reference_model="ar1",
    )
    assert cards[0].n > 0
    assert cards[0].rmse is not None
    assert cards[0].rmse_ratio_vs_reference == pytest.approx(1.0)
    assert cards[0].coverage_80 is not None
    assert cards[0].direction_accuracy is not None
    assert cards[1].model_name == "last_value"
    assert cards[1].rmse_ratio_vs_reference is not None


def test_chart_builds_without_error() -> None:
    bundle = load_dashboard_bundle(prefer_fixture=True)
    hist = history_frame(bundle.joined, "ar1")
    assert not hist.empty
    chart = predictions_vs_actuals_chart(bundle.joined, "ar1")
    assert chart is not None


def test_copy_mentions_honest_ar1_limits() -> None:
    assert "AR(1)" in LIMITS
    assert "nowcast" in HOW_IT_WORKS.lower()
    assert "stored logs" in HOW_IT_WORKS.lower()


def test_app_package_layout() -> None:
    required = [
        "src/nowcaster/app/streamlit_app.py",
        "src/nowcaster/app/load_logs.py",
        "src/nowcaster/app/scoreboard.py",
        "src/nowcaster/app/charts.py",
        "src/nowcaster/app/copy_text.py",
        "src/nowcaster/app/fixtures/predictions.csv",
        "src/nowcaster/app/fixtures/scores.csv",
        "src/nowcaster/app/fixtures/dashboard_meta.json",
        "streamlit_app.py",
        "docs/streamlit_deploy.md",
    ]
    missing = [p for p in required if not (ROOT / p).exists()]
    assert not missing, missing


def test_streamlit_entrypoint_importable() -> None:
    import nowcaster.app.streamlit_app as app_mod

    assert callable(app_mod.render)
